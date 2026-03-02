import requests
import time
import json
import sys

URL = "http://127.0.0.1:8000/review-code"

payload = {
    "code": """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

print(add(5, 3))
print(subtract(10, 4))""",
    "language": "Python"
}


def test_review_api():
    """Test the /review-code endpoint."""
    print("=" * 50)
    print("IntelliReview API Test")
    print("=" * 50)
    print(f"\nTarget: {URL}")
    print("Sending request...\n")

    try:
        start_time = time.time()
        response = requests.post(URL, json=payload, timeout=30)
        elapsed = round(time.time() - start_time, 2)

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed} seconds\n")

        if response.status_code != 200:
            print(f"ERROR: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

        data = response.json()
        print("Response JSON:\n")
        print(json.dumps(data, indent=4))

        # Validate response structure
        required_keys = ["quality_score", "issues", "ai_explanation", "fixed_code"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            print(f"\nWARNING: Missing keys in response: {missing}")
        else:
            print("\n✅ All required fields present!")

        # Check score validity
        score = data.get("quality_score", "")
        if score not in ("N/A", "Error") and str(score).replace(".", "").isdigit():
            print(f"✅ Quality score: {score}/10")
        else:
            print(f"⚠️  Quality score: {score} (not a numeric score)")

    except requests.ConnectionError:
        print("ERROR: Cannot connect to server. Is it running?")
        print("Start it with: uvicorn main:app --reload")
        sys.exit(1)
    except requests.Timeout:
        print("ERROR: Request timed out after 30 seconds.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_review_api()