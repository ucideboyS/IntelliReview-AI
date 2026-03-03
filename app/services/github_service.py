import os
import json
import re
import logging

from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import ValidationError

from app.models.review_response import ReviewResponse

load_dotenv()

logger = logging.getLogger(__name__)

# GitHub token is loaded but NEVER logged
_github_token = os.getenv("GITHUB_TOKEN")

client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=_github_token
)

PROMPT_TEMPLATE = """\
You are an expert {language} code reviewer.

Analyze the following {language} code carefully and respond ONLY with valid JSON.
No markdown, no backticks, no extra text — pure JSON only.

You MUST return ALL of the following fields with numeric scores (floats between 0 and 10):

{{
  "readability":      <float 0-10>,
  "performance":      <float 0-10>,
  "maintainability":  <float 0-10>,
  "security":         <float 0-10>,
  "best_practices":   <float 0-10>,
  "overall_score":    <float 0-10>,
  "issues":           "<string — describe all issues found, or 'No issues found.'>",
  "ai_explanation":   "<string — brief explanation of the overall code quality>",
  "fixed_code":       "<string — corrected version of the code, or 'No fix needed.'>"
}}

Rules:
- All score fields MUST be numbers, not strings.
- overall_score should reflect the weighted average of the 5 dimension scores.
- Be specific and actionable in issues and ai_explanation.

Code:
{code}
"""

# Max characters sent to AI per file (token guard)
MAX_CODE_CHARS = 3000


async def analyze_code_with_fix(code: str, language: str = "Python") -> dict:
    """
    Send code to GitHub Models (GPT-4.1-nano) for multi-dimensional review.
    Returns validated dict with 6 scores + issues + explanation + fixed_code + token_usage.
    """
    # Enforce per-call truncation as second layer of defense
    truncated_code = code[:MAX_CODE_CHARS]

    prompt = PROMPT_TEMPLATE.format(language=language, code=truncated_code)

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        raw_output = response.choices[0].message.content.strip()

        # Log token usage (safe — no secrets)
        token_usage = None
        if response.usage:
            token_usage = response.usage.total_tokens
            logger.info(
                f"Token usage — prompt: {response.usage.prompt_tokens}, "
                f"completion: {response.usage.completion_tokens}, "
                f"total: {response.usage.total_tokens}"
            )

        # Strip markdown code fences if model adds them
        raw_output = re.sub(r"```json|```", "", raw_output).strip()

        # Extract JSON block
        json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON block found in model output.")

        parsed = json.loads(json_match.group(0))

        # Strict Pydantic validation
        validated = ReviewResponse(**parsed)
        result = validated.model_dump()
        result["token_usage"] = token_usage
        return result

    except (json.JSONDecodeError, ValueError, ValidationError) as e:
        logger.warning(f"AI response parse/validation failed: {e}")
        return _fallback_response(str(e))

    except Exception as e:
        # Never expose raw exception (may contain API details) in return value
        logger.error(f"GitHub Models API call failed: {type(e).__name__}")
        return _fallback_response("API call failed.", api_error=True)


def _fallback_response(detail: str, api_error: bool = False) -> dict:
    """Return a safe fallback when AI output cannot be parsed or validated."""
    issue_msg = (
        "GitHub Models API call failed."
        if api_error
        else "Model did not return valid structured JSON."
    )
    return {
        "readability":     0.0,
        "performance":     0.0,
        "maintainability": 0.0,
        "security":        0.0,
        "best_practices":  0.0,
        "overall_score":   0.0,
        "issues":          issue_msg,
        "ai_explanation":  detail,
        "fixed_code":      "No fix generated.",
        "token_usage":     None,
    }