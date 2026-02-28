import os
import json
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("GITHUB_TOKEN")
)


async def analyze_code_with_fix(code: str, language: str = "Python") -> dict:
    """
    Send code to GitHub Models (GPT-4o mini) for review.
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
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        raw_output = response.choices[0].message.content.strip()

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
            "issues": "GitHub Models API call failed.",
            "ai_explanation": str(e),
            "fixed_code": "No fix generated."
        }