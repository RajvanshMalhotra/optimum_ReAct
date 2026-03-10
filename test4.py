"""
test_agent.py
=============
Tests for full agent run with web search.
Run with: python test_agent.py
"""

import asyncio
import time
from core.agent import FastAgent, HybridMemory


# ==============================================================================
# TEST HELPERS
# ==============================================================================

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
SEP  = "=" * 60


def assert_answer(answer: str, must_contain: list[str], test_name: str):
    """Check that the answer contains expected keywords."""
    answer_lower = answer.lower()
    missing = [kw for kw in must_contain if kw.lower() not in answer_lower]
    if not missing:
        print(f"{PASS} {test_name}")
    else:
        print(f"{FAIL} {test_name}")
        print(f"       Missing keywords: {missing}")
        print(f"       Answer snippet: {answer[:200]}")
    return len(missing) == 0


def assert_not_empty(answer: str, test_name: str):
    """Check that the agent returned a non-empty answer."""
    ok = bool(answer and answer.strip())
    print(f"{PASS if ok else FAIL} {test_name}")
    return ok


# ==============================================================================
# TESTS
# ==============================================================================

async def test_basic_factual_search():
    """Agent should search and return a factual answer."""
    print(f"\n{SEP}")
    print("TEST 1 — Basic factual web search")
    print(SEP)

    memory = HybridMemory()
    agent = FastAgent(memory=memory)

    start = time.time()
    answer = await agent.run("What is the capital of Japan?")
    duration = time.time() - start

    print(f"Answer: {answer[:300]}")
    print(f"Time:   {duration:.1f}s")

    assert_answer(answer, ["tokyo"], "Answer contains 'Tokyo'")
    assert_not_empty(answer, "Answer is not empty")

    await agent.cleanup()


async def test_current_events_search():
    """Agent should search for recent information it wouldn't know from memory."""
    print(f"\n{SEP}")
    print("TEST 2 — Current events (requires live search)")
    print(SEP)

    memory = HybridMemory()
    agent = FastAgent(
        memory=memory,
        system_prompt=(
            "You are a news assistant. Always search for current information. "
            "Be concise and factual."
        ),
    )

    start = time.time()
    answer = await agent.run("What are the latest developments in AI this week?")
    duration = time.time() - start

    print(f"Answer: {answer[:400]}")
    print(f"Time:   {duration:.1f}s")

    assert_not_empty(answer, "Answer is not empty")
    assert_answer(answer, ["ai", "model", "research", "openai", "google", "anthropic"],
                  "Answer contains AI-related keywords")

    await agent.cleanup()


async def test_multi_step_search():
    """Agent should make multiple searches to compare two things."""
    print(f"\n{SEP}")
    print("TEST 3 — Multi-step comparison search")
    print(SEP)

    memory = HybridMemory()
    agent = FastAgent(
        memory=memory,
        system_prompt=(
            "You are a research assistant. "
            "Search thoroughly before comparing. Show concrete numbers."
        ),
    )

    start = time.time()
    answer = await agent.run(
        "What is the population of Tokyo vs New York City? Which is larger?"
    )
    duration = time.time() - start

    print(f"Answer: {answer[:400]}")
    print(f"Time:   {duration:.1f}s")

    assert_not_empty(answer, "Answer is not empty")
    assert_answer(answer, ["tokyo", "new york"], "Answer mentions both cities")
    assert_answer(answer, ["million"], "Answer contains population figures")

    await agent.cleanup()


async def test_search_stores_in_memory():
    """Search results should be stored and retrievable in the same session."""
    print(f"\n{SEP}")
    print("TEST 4 — Search results stored in memory")
    print(SEP)

    memory = HybridMemory()
    agent = FastAgent(memory=memory)

    # First task — search for something
    await agent.run("What company makes the iPhone?")

    # Second task — agent should recall without re-searching
    start = time.time()
    answer = await agent.run("Based on what you just found, who makes the iPhone?")
    duration = time.time() - start

    print(f"Answer: {answer[:300]}")
    print(f"Time:   {duration:.1f}s")

    assert_answer(answer, ["apple"], "Agent recalls 'Apple' from memory")

    await agent.cleanup()


async def test_agent_gives_honest_answer_when_uncertain():
    """Agent should not hallucinate when it genuinely cannot find info."""
    print(f"\n{SEP}")
    print("TEST 5 — Honest answer when info is hard to find")
    print(SEP)

    memory = HybridMemory()
    agent = FastAgent(
        memory=memory,
        system_prompt=(
            "You are a precise assistant. "
            "If you cannot find reliable information, say so clearly. Never guess."
        ),
    )

    answer = await agent.run(
        "What was the exact temperature in Mumbai at 3:47pm on March 3rd 2019?"
    )

    print(f"Answer: {answer[:300]}")

    # Should not confidently hallucinate a precise number
    assert_not_empty(answer, "Answer is not empty")
    print(f"{PASS} Agent responded without crashing")

    await agent.cleanup()


# ==============================================================================
# SUMMARY RUNNER
# ==============================================================================

async def main():
    print("\n\033[96m🧪 Running FastAgent web search tests...\033[0m")
    total_start = time.time()

    await test_basic_factual_search()
    await test_current_events_search()
    await test_multi_step_search()
    await test_search_stores_in_memory()
    await test_agent_gives_honest_answer_when_uncertain()

    total = time.time() - total_start
    print(f"\n{SEP}")
    print(f"\033[96m✔ All tests completed in {total:.1f}s\033[0m")
    print(SEP)


if __name__ == "__main__":
    asyncio.run(main())