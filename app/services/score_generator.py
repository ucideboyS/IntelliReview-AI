import re


def generate_score(pylint_output: str) -> str:
    """
    Extract the quality score from pylint output.

    Args:
        pylint_output: Raw stdout string from pylint.

    Returns:
        Score string like "8.50" or "N/A" if not found.
    """
    if not pylint_output or not isinstance(pylint_output, str):
        return "N/A"

    match = re.search(r"rated at ([\d.]+)/10", pylint_output)
    if match:
        try:
            score_value = float(match.group(1))
            if 0.0 <= score_value <= 10.0:
                return str(round(score_value, 2))
        except ValueError:
            pass

    return "N/A"
