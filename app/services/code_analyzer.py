import tempfile
import subprocess
import os


def analyze_code(code: str) -> dict:
    """
    Run pylint on the provided code string.

    Args:
        code: Python source code as a string.

    Returns:
        dict with stdout, stderr, returncode, or an error key.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pylint", tmp_path, "--output-format=text"],
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        return {"error": "pylint is not installed. Run: pip install pylint"}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
