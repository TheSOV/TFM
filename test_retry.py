import asyncio
# if the decorator lives at src/retry_mechanism/retry.py:
from src.retry_mechanism.retry import retry_with_feedback  

# --------------------------------------------------------------------
# Async flaky function that fails twice, then succeeds on the 3rd try
# --------------------------------------------------------------------
attempt_counter = {"n": 0}

@retry_with_feedback(max_attempts=3, delay=0.2)  # three attempts, 0.2 s apart
async def flaky_async_demo(feedback=None):
    """
    Demonstrates retry_with_feedback on an *async* function.
    It raises twice, then returns successfully on the third call.
    """
    print("flaky_async_demo called with feedback:", feedback)
    attempt_counter["n"] += 1

    if attempt_counter["n"] < 3:
        raise RuntimeError("Kaboom async 💥")  # trigger a retry

    # third call succeeds
    return "🎉 async success!"


# --------------------------------------------------------------------
# Hand-rolled main() runner
# --------------------------------------------------------------------
async def main():
    fb = {"value": ""}          # mutable dict that will collect the log
    result = await flaky_async_demo(feedback=fb)

    print("\nResult:", result)
    print("\n--- feedback log ---")
    print(fb["value"])


if __name__ == "__main__":
    asyncio.run(main())
