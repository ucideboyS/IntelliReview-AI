import os
import json
import re
import logging
from typing import Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import ValidationError

from app.models.review_response import ReviewResponse

load_dotenv()

logger = logging.getLogger(__name__)

# GitHub token loaded but NEVER logged
_github_token = os.getenv("GITHUB_TOKEN")

client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=_github_token,
)

# ── PROMPT ──────────────────────────────────────────────────────────────────
# Uses 2-message approach (system + user) to avoid all str.format() brace issues.

SYSTEM_PROMPT = (
    "You are an expert code reviewer and bug fixer.\n"
    "You analyze code and respond ONLY with valid JSON — no markdown, no backticks, no extra text.\n\n"
    "You MUST return a JSON object with these exact fields:\n"
    "{\n"
    '  "readability":      <float 0-10>,\n'
    '  "performance":      <float 0-10>,\n'
    '  "maintainability":  <float 0-10>,\n'
    '  "security":         <float 0-10>,\n'
    '  "best_practices":   <float 0-10>,\n'
    '  "overall_score":    <float 0-10>,\n'
    '  "issues":           "<string>",\n'
    '  "ai_explanation":   "<string>",\n'
    '  "fixed_code":       "<string>"\n'
    "}\n\n"
    "RULES:\n"
    "1. All score fields MUST be numbers (floats), NOT strings.\n"
    "2. overall_score = weighted average of the 5 dimension scores.\n"
    "3. issues: list EVERY bug, vulnerability, and bad practice found. "
    "If none, write 'No issues found.'\n"
    "4. ai_explanation: brief summary of overall code quality.\n"
    "5. fixed_code: the COMPLETE corrected version of the code with ALL bugs fixed.\n"
    "   - Fix EVERY issue you listed in the issues field.\n"
    "   - Must be complete, runnable code — not a snippet or partial.\n"
    "   - Use \\n for newlines inside the JSON string value.\n"
    "   - Properly escape all quotes and backslashes for valid JSON.\n"
    "   - If the fixed code would be very long (>80 lines), provide a shorter "
    "corrected version focusing on the most critical fixes only.\n"
    "   - If no issues exist, set to 'No fix needed.'\n"
    "6. Your entire response must be ONE valid JSON object. Nothing else."
)

# Max characters sent to AI per file
MAX_CODE_CHARS = 4000


def _build_user_message(code: str, language: str) -> str:
    """Build the user message with the code to review."""
    return (
        f"Review this {language} code. Respond with valid JSON only.\n\n"
        f"```{language.lower()}\n"
        f"{code}\n"
        f"```"
    )


def _extract_json_object(text: str) -> Optional[dict]:
    """
    Extract and parse the first complete JSON object from text.
    Uses brace-depth counting for accuracy, falls back to regex.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            escape_next = True
            continue

        if ch == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break

    # Fallback: regex
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _try_recover_from_truncated(raw: str) -> Optional[dict]:
    """
    Recover scores and issues from a truncated AI response.
    
    Common failure: AI returns valid scores + issues, but fixed_code
    gets cut off mid-string → 'Unterminated string' JSON error.
    This extracts everything we can still use.
    """
    try:
        def extract_float(key: str) -> float:
            m = re.search(rf'"{key}"\s*:\s*([0-9]+\.?[0-9]*)', raw)
            return float(m.group(1)) if m else 0.0

        def extract_string(key: str) -> str:
            m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            return m.group(1).replace("\\n", "\n").replace('\\"', '"') if m else ""

        readability = extract_float("readability")
        performance = extract_float("performance")
        maintainability = extract_float("maintainability")
        security = extract_float("security")
        best_practices = extract_float("best_practices")
        overall_score = extract_float("overall_score")
        issues = extract_string("issues")
        ai_explanation = extract_string("ai_explanation")

        # Only succeed if we got real scores
        if overall_score > 0 and (issues or ai_explanation):
            logger.info(
                f"Recovered partial response — scores extracted "
                f"(overall: {overall_score}), fixed_code was truncated."
            )
            return {
                "readability": readability,
                "performance": performance,
                "maintainability": maintainability,
                "security": security,
                "best_practices": best_practices,
                "overall_score": overall_score,
                "issues": issues or "Could not extract issues from truncated response.",
                "ai_explanation": ai_explanation or "Response was partially truncated.",
                "fixed_code": (
                    "The AI response was too long and got truncated. "
                    "Review the issues listed above and apply the fixes manually."
                ),
            }
    except Exception as e:
        logger.debug(f"Recovery attempt failed: {e}")

    return None


async def analyze_code_with_fix(code: str, language: str = "Python") -> dict:
    """
    Send code to GitHub Models (GPT-4.1-nano) for multi-dimensional review.

    Uses a 2-message approach (system + user) — completely avoids str.format()
    brace-escaping problems. Returns validated dict with 6 scores + issues
    + explanation + fixed_code + token_usage.
    """
    truncated_code = code[:MAX_CODE_CHARS]
    user_message = _build_user_message(truncated_code, language)

    raw_output = ""
    token_usage = None

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            timeout=45,
        )

        raw_output = response.choices[0].message.content.strip()

        # Log token usage — safe, contains no secrets
        if response.usage:
            token_usage = response.usage.total_tokens
            logger.info(
                f"Token usage — prompt: {response.usage.prompt_tokens}, "
                f"completion: {response.usage.completion_tokens}, "
                f"total: {response.usage.total_tokens}"
            )

        # Strip markdown fences if model wraps response
        raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
        raw_output = re.sub(r"\s*```\s*$", "", raw_output).strip()

        # Try to extract a complete JSON object
        parsed = _extract_json_object(raw_output)

        if parsed is None:
            # JSON extraction failed — try recovery from truncated response
            logger.warning("No complete JSON found. Attempting truncated recovery...")
            recovered = _try_recover_from_truncated(raw_output)
            if recovered:
                recovered["token_usage"] = token_usage
                return recovered
            raise ValueError("No valid JSON block found in model output.")

        # Strict Pydantic validation
        validated = ReviewResponse(**parsed)
        result = validated.model_dump()
        result["token_usage"] = token_usage
        return result

    except (json.JSONDecodeError, ValueError, ValidationError) as e:
        logger.warning(f"AI response parse/validation failed: {e}")

        # One more recovery attempt on the raw output
        if raw_output:
            recovered = _try_recover_from_truncated(raw_output)
            if recovered:
                recovered["token_usage"] = token_usage
                return recovered

        return _fallback_response(str(e))

    except Exception as e:
        # Never expose raw exception — may contain API key details
        logger.error(f"GitHub Models API call failed: {type(e).__name__}")
        return _fallback_response(
            "GitHub Models API call failed — check GITHUB_TOKEN and network.",
            api_error=True,
        )


def _fallback_response(detail: str, api_error: bool = False) -> dict:
    """Return a safe zero-score fallback when the AI call or parse fails."""
    issue_msg = (
        "GitHub Models API call failed — check GITHUB_TOKEN and network."
        if api_error
        else "Analysis failed — the AI model did not return a valid response. Try again."
    )
    return {
        "readability": 0.0,
        "performance": 0.0,
        "maintainability": 0.0,
        "security": 0.0,
        "best_practices": 0.0,
        "overall_score": 0.0,
        "issues": issue_msg,
        "ai_explanation": detail,
        "fixed_code": "No fix generated.",
        "token_usage": None,
    }