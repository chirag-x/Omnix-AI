
import time
from openai import OpenAI


# ============================================================
# OMNIROUTE CONFIGURATION
# ============================================================

BASE_URL = "http://localhost:20128/v1"

# IMPORTANT:
# Use your NEW OmniRoute API key here.
API_KEY = "sk-91d3746c342d6cf3-ba40b7-c856582b"


# ============================================================
# MODELS TO TEST
# ============================================================
#
# Add/remove models from this list.
#
# These IDs come from the /v1/models output you showed.
#

MODELS = [
    # Antigravity
    "antigravity/gemini-3.6-flash-medium",
    "antigravity/gemini-3.6-flash-high",
    "antigravity/claude-sonnet-4-6",
    "antigravity/claude-opus-4-6-thinking",

]


# ============================================================
# TEST MESSAGE
# ============================================================

TEST_MESSAGE = """
You are being tested as the brain of a desktop AI assistant.

Reply with exactly this sentence and nothing else:

OmniRoute model test successful.
""".strip()


# ============================================================
# VALIDATION
# ============================================================

if API_KEY == "PASTE_YOUR_NEW_OMNIROUTE_API_KEY_HERE":
    print("=" * 70)
    print("ERROR: OmniRoute API key has not been entered.")
    print("=" * 70)
    print()
    print("Open this file and replace:")
    print()
    print('API_KEY = "PASTE_YOUR_NEW_OMNIROUTE_API_KEY_HERE"')
    print()
    print("with your OmniRoute API key.")
    raise SystemExit(1)


# ============================================================
# CREATE CLIENT
# ============================================================

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
    timeout=60.0,
)


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 70)
print("OMNIROUTE MODEL TEST")
print("=" * 70)
print()
print("Base URL:")
print(BASE_URL)
print()
print(f"Models to test: {len(MODELS)}")
print()


# ============================================================
# CHECK CONNECTION FIRST
# ============================================================

print("[1] Checking OmniRoute connection...")
print()

try:
    available_models = client.models.list()

    available_ids = {
        model.id
        for model in available_models.data
    }

    print("OmniRoute connection: SUCCESS")
    print(f"Models available from server: {len(available_ids)}")

except Exception as e:
    print("OmniRoute connection: FAILED")
    print()
    print("Error:")
    print(e)
    print()
    print("Make sure OmniRoute is running on:")
    print(BASE_URL)
    raise SystemExit(1)


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# TEST EACH MODEL
# ============================================================

print()
print("=" * 70)
print("[2] TESTING MODELS")
print("=" * 70)
print()


for index, model in enumerate(MODELS, start=1):

    print(f"[{index}/{len(MODELS)}] {model}")

    # --------------------------------------------------------
    # Check whether model appears in /v1/models
    # --------------------------------------------------------

    if model not in available_ids:
        print("  STATUS: NOT FOUND")
        print("  The model ID is not currently exposed by OmniRoute.")
        print()

        results.append({
            "model": model,
            "status": "NOT FOUND",
            "time": None,
            "response": None,
            "error": "Model not returned by /v1/models",
        })

        continue

    # --------------------------------------------------------
    # Send request
    # --------------------------------------------------------

    start_time = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": TEST_MESSAGE,
                }
            ],
            temperature=0,
        )

        elapsed = time.perf_counter() - start_time

        answer = response.choices[0].message.content

        print(f"  STATUS: PASS")
        print(f"  TIME:   {elapsed:.2f}s")
        print(f"  REPLY:  {answer}")

        results.append({
            "model": model,
            "status": "PASS",
            "time": elapsed,
            "response": answer,
            "error": None,
        })

    except Exception as e:

        elapsed = time.perf_counter() - start_time

        print(f"  STATUS: FAIL")
        print(f"  TIME:   {elapsed:.2f}s")
        print(f"  ERROR:  {e}")

        results.append({
            "model": model,
            "status": "FAIL",
            "time": elapsed,
            "response": None,
            "error": str(e),
        })

    print()


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("FINAL RESULTS")
print("=" * 70)
print()

print(
    f"{'MODEL':<55} {'STATUS':<12} {'TIME':>8}"
)
print("-" * 70)


for result in results:

    model = result["model"]
    status = result["status"]

    if result["time"] is None:
        time_text = "-"
    else:
        time_text = f"{result['time']:.2f}s"

    # Keep long model names readable
    display_model = model

    if len(display_model) > 55:
        display_model = display_model[:52] + "..."

    print(
        f"{display_model:<55} "
        f"{status:<12} "
        f"{time_text:>8}"
    )


# ============================================================
# COUNTS
# ============================================================

passed = sum(
    1 for result in results
    if result["status"] == "PASS"
)

failed = sum(
    1 for result in results
    if result["status"] == "FAIL"
)

not_found = sum(
    1 for result in results
    if result["status"] == "NOT FOUND"
)


print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()

print(f"Total tested : {len(results)}")
print(f"PASS         : {passed}")
print(f"FAIL         : {failed}")
print(f"NOT FOUND    : {not_found}")
print()


# ============================================================
# WORKING MODELS
# ============================================================

if passed > 0:

    print("=" * 70)
    print("WORKING MODELS")
    print("=" * 70)
    print()

    working = [
        result
        for result in results
        if result["status"] == "PASS"
    ]

    # Sort by response time
    working.sort(
        key=lambda result: result["time"]
    )

    for result in working:
        print(
            f"{result['model']}"
            f"  ->  {result['time']:.2f}s"
        )

    print()


# ============================================================
# FAILED MODELS
# ============================================================

if failed > 0:

    print("=" * 70)
    print("FAILED MODELS")
    print("=" * 70)
    print()

    for result in results:

        if result["status"] == "FAIL":

            print(result["model"])
            print(f"  Error: {result['error']}")
            print()


# ============================================================
# FINISHED
# ============================================================

print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print()
