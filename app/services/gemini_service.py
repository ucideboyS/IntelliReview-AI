import os
from google import genai
from dotenv import load_dotenv
import json
import re

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def analyze_code_with_fix(code: str, language: str = "Python") -> dict:
    """
    Send code to Gemini AI for review.
    Returns structured dict with quality_score, issues, ai_explanation, fixed_code.
    """

    prompt = f"""
You are an expert {language} code reviewer.

Analyze the following {language} code carefully.

Respond ONLY in valid JSON.
Do NOT include explanations outside JSON.
Do NOT include markdown.
Do NOT include backticks.

Format EXACTLY like this:

{{
  "quality_score": "number from 1-10",
  "issues": "clear description of issues or 'No issues found.'",
  "ai_explanation": "short explanation of the code quality",
  "fixed_code": "corrected code or 'No fix needed.'"
}}

Code:
{code}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )

        raw_output = response.text.strip()

        # Strip markdown code fences if model adds them
        raw_output = re.sub(r"```json|```", "", raw_output).strip()

        # Extract JSON block
        json_match = re.search(r"\{.*?\}", raw_output, re.DOTALL)

        if json_match:
            clean_json = json_match.group(0)
            try:
                return json.loads(clean_json)
            except json.JSONDecodeError:
                pass

        return {
            "quality_score": "N/A",
            "issues": "Model did not return structured JSON.",
            "ai_explanation": raw_output,
            "fixed_code": "No fix generated."
        }

    except Exception as e:
        return {
            "quality_score": "Error",
            "issues": "Gemini API call failed.",
            "ai_explanation": str(e),
            "fixed_code": "No fix generated."
        }