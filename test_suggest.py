"""Simple test script to call POST /suggest on the backend."""
import sys
import json

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)

API = "http://localhost:8000/suggest"

def test(question="How do I reset my password?"):
    payload = {"question": question}
    try:
        r = requests.post(API, json=payload, timeout=5)
    except Exception as e:
        print(f"Request failed: {e}")
        return 2

    print(f"Status: {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
    return 0

if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else None
    if q:
        sys.exit(test(q))
    sys.exit(test())
