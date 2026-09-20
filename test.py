
from openai import OpenAI


# ============================================================
# OMNIROUTE CONFIG
# ============================================================

BASE_URL = "http://localhost:20128/v1"

# Use your NEW key here after regenerating the exposed key.
API_KEY = "sk-91d3746c342d6cf3-ba40b7-c856582b"

MODEL = "antigravity/gemini-3.6-flash-high"
# MODEL = "auto/best-coding"



# ============================================================
# CREATE CLIENT
# ============================================================

print("=" * 60)
print("OMNIROUTE TEST")
print("=" * 60)

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)


# ============================================================
# TEST 1 - GET MODELS
# ============================================================

print()
print("[1] Testing /v1/models...")

try:
    models = client.models.list()

    print("SUCCESS")
    print()
    print("Available models:")

    for model in models.data:
        print("  -", model.id)

except Exception as e:
    print("FAILED")
    print("Error:", e)
    raise SystemExit(1)


# ============================================================
# TEST 2 - CHAT COMPLETION
# ============================================================

print()
print("[2] Testing chat completion...")
print("Model:", MODEL)
print()

try:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: OmniRoute is working."
            }
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content

    print("=" * 60)
    print("CHAT TEST SUCCESS")
    print("=" * 60)
    print()
    print("Response:")
    print(answer)
    print()

except Exception as e:
    print("=" * 60)
    print("CHAT TEST FAILED")
    print("=" * 60)
    print()
    print("Error:", e)
    print()

    raise SystemExit(1)


# ============================================================
# FINAL RESULT
# ============================================================

print("=" * 60)
print("FINAL RESULT")
print("=" * 60)
print()
print("OmniRoute server : WORKING")
print("API key          : WORKING")
print("Model discovery  : WORKING")
print("Selected model   :", MODEL)
print("Chat completion  : WORKING")
print()
print("OmniRoute is ready to be connected to Omnix.")
