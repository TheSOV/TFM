"""
retry_with_feedback.py
----------------------

A drop-in retry decorator that:

* works for **sync _and_ async** callables
* logs each failed attempt into a caller-supplied feedback dict
* appends a single “Final error …” line only if all retries are exhausted
* uses Tenacity’s `wait_fixed` so you don’t have to write your own sleeps
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Type, TypeVar, Union

from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    RetryCallState,
)

T = TypeVar("T")  # Return type of the decorated function


# ---------------------------------------------------------------------------
# Helper that Tenacity calls *after every attempt* (success or failure).
# We use it to accumulate the "Attempt N failed: …" lines.
# ---------------------------------------------------------------------------
class RetryFeedback:
    def __init__(self, feedback_ref: dict[str, str]):
        self.feedback_ref = feedback_ref

    def __call__(self, retry_state: RetryCallState) -> None:
        if retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
            attempt = retry_state.attempt_number
            msg = f"Attempt {attempt} failed: {exc}"
            self.feedback_ref["value"] = (
                f"{self.feedback_ref['value']}\n{msg}" if self.feedback_ref["value"] else msg
            )


# ---------------------------------------------------------------------------
# The decorator factory
# ---------------------------------------------------------------------------
def retry_with_feedback(
    max_attempts: int = 3,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    delay: float = 1.0,
    feedback_param: str = "feedback",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Usage::

        @retry_with_feedback(max_attempts=3, delay=0.5)
        def my_func(arg1, *, feedback=None):
            ...

    The decorated function **should** accept a kwarg named `feedback`
    (or whatever you pass in `feedback_param`).  Pass in a dict
    ``{"value": ""}``; the decorator appends log lines to it.
    """

    # -- internal helpers ----------------------------------------------------

    def _ensure_feedback_dict(kwargs: dict[str, Any]) -> dict[str, str]:
        fb = kwargs.get(feedback_param)
        if fb is None:
            fb = {"value": ""}
            kwargs[feedback_param] = fb
        return fb

    def _append_final_error(feedback: dict[str, str], exc: Exception) -> None:
        final = f"Final error: {exc}"
        feedback["value"] = f"{feedback['value']}\n{final}" if feedback["value"] else final

    def _make_retry(feedback: dict[str, str]):
        return tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_fixed(delay),
            retry=retry_if_exception_type(exceptions),
            after=RetryFeedback(feedback),  # logs each failed attempt
            reraise=True,  # propagate the last exception if all retries fail
        )

    # -- the real decorator --------------------------------------------------

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        is_async = asyncio.iscoroutinefunction(func)

        # ----------- ASYNC version ------------------------------------------
        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                feedback = _ensure_feedback_dict(kwargs)

                @_make_retry(feedback)
                async def _wrapped():
                    return await func(*args, **kwargs)

                try:
                    return await _wrapped()
                except Exception as exc:  # only reached after the *last* attempt
                    _append_final_error(feedback, exc)
                    raise

            return async_wrapper  # type: ignore[return-value]

        # ----------- SYNC version -------------------------------------------
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                feedback = _ensure_feedback_dict(kwargs)

                @_make_retry(feedback)
                def _wrapped():
                    return func(*args, **kwargs)

                try:
                    return _wrapped()
                except Exception as exc:  # only reached after the *last* attempt
                    _append_final_error(feedback, exc)
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Quick-start demos
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # ---------- synchronous demo ----------------------------------------
    print("=== SYNC DEMO ===")
    sync_counter = {"n": 0}

    @retry_with_feedback(max_attempts=3, delay=0.2)
    def flaky_sync(feedback=None):
        print("Flaky sync called with feedback:", feedback)
        sync_counter["n"] += 1
        print("flaky_sync called; attempt", sync_counter["n"])
        if sync_counter["n"] < 3:
            raise RuntimeError("Kaboom sync 💥")
        return "✅ sync OK"

    fb_sync = {"value": ""}
    print("Result:", flaky_sync(feedback=fb_sync))
    print("--- feedback log ---\n", fb_sync["value"], "\n")

    # ---------- asynchronous demo ---------------------------------------
    print("=== ASYNC DEMO ===")
    async_counter = {"n": 0}

    @retry_with_feedback(max_attempts=3, delay=0.2)
    async def flaky_async(feedback=None):
        print("Flaky async called with feedback:", feedback)
        async_counter["n"] += 1
        print("flaky_async called; attempt", async_counter["n"])
        if async_counter["n"] < 3:
            raise RuntimeError("Kaboom async 💥")
        return "✅ async OK"

    async def run_async_demo():
        fb_async = {"value": ""}
        result = await flaky_async(feedback=fb_async)
        # print("Result:", result)
        # print("--- feedback log ---\n", fb_async["value"])

    asyncio.run(run_async_demo())
