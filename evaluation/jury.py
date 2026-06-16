"""
Adversarial jury evaluator.

Problem with LLM-as-judge: a single judge gets sycophancy bias — it prefers
verbose, confident-sounding answers even when they're wrong.

Solution: 3 independent jurors (accuracy, conciseness, relevance) + 1 adversary
that actively argues AGAINST the answer after seeing the initial scores. Jurors
then revise. The score_delta field tells you how effective the adversary was —
low delta means jurors either stood their ground or the adversary was weak.
"""
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Optional
from core.llm import llm_client


# ── Juror prompts ─────────────────────────────────────────────────────────────

_JUROR_PROMPTS = {
    "accuracy": """\
You are an ACCURACY judge. Score whether this answer is factually correct and complete.

QUERY: {query}
ANSWER: {answer}

Scoring guide:
10 = all facts correct, nothing important missing
7  = mostly accurate, minor gaps or imprecision
4  = partially accurate, significant gaps or errors
1  = mostly incorrect or misleading

Respond with valid JSON only:
{{"score": <1-10>, "reasoning": "specific accuracy assessment in 1-2 sentences"}}""",

    "conciseness": """\
You are a CONCISENESS judge. Score whether this answer is appropriately concise.

QUERY: {query}
ANSWER: {answer}

Scoring guide:
10 = perfectly sized, no wasted words, no missing substance
7  = good length, minor padding or minor gaps
4  = significantly too long (padding) or too short (incomplete)
1  = severely bloated or practically empty

Respond with valid JSON only:
{{"score": <1-10>, "reasoning": "specific conciseness assessment in 1-2 sentences"}}""",

    "relevance": """\
You are a RELEVANCE judge. Score whether this answer directly addresses what was asked.

QUERY: {query}
ANSWER: {answer}

Scoring guide:
10 = directly answers the exact question, no tangents
7  = mostly on-point, minor irrelevant content
4  = partially relevant, misses key aspects of the question
1  = mostly off-topic or answers a different question

Respond with valid JSON only:
{{"score": <1-10>, "reasoning": "specific relevance assessment in 1-2 sentences"}}""",
}

_ADVERSARY_PROMPT = """\
You are a CRITICAL ADVERSARY. Your job: aggressively challenge this answer and the scores the jurors gave it.
Find every flaw, gap, unverified claim, and logical weakness you can.

QUERY: {query}
ANSWER: {answer}

INITIAL JUROR SCORES:
- Accuracy:    {accuracy_score}/10 — {accuracy_reasoning}
- Conciseness: {conciseness_score}/10 — {conciseness_reasoning}
- Relevance:   {relevance_score}/10 — {relevance_reasoning}

Write a structured critique attacking:
1. What KEY information is missing from the answer?
2. What claims are UNVERIFIED or potentially wrong?
3. Does the answer actually SOLVE the user's problem, or just sound good?
4. Are the jurors being too lenient? Which scores are inflated?

Be specific. Name the exact gaps and flaws.

Respond with valid JSON only:
{{"critique": "your detailed critique", "jurors_too_lenient": <true/false>}}"""

_REVISION_PROMPT = """\
You previously scored this answer. An adversary has now critiqued it.
Decide whether to revise your score based on the critique.

QUERY: {query}
ANSWER: {answer}
YOUR ORIGINAL SCORE: {original_score}/10
YOUR REASONING: {original_reasoning}

ADVERSARY'S CRITIQUE:
{critique}

If the adversary raised valid, specific points you missed — lower your score.
If the critique is vague, unfair, or doesn't apply to your dimension — keep your score.

Respond with valid JSON only:
{{"revised_score": <1-10>, "changed": <true/false>, "justification": "why you changed or kept your score"}}"""


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class JuryVerdict:
    final_score: float
    accuracy: float
    relevance: float
    conciseness: float
    adversary_critique: str
    score_delta: float          # avg absolute shift caused by adversary — calibration signal
    jurors_too_lenient: bool
    model: str = ""


# ── Evaluator ─────────────────────────────────────────────────────────────────

class JuryEvaluator:
    """
    3-round adversarial jury:
      Round 1 — 3 jurors score independently (parallel)
      Round 2 — adversary writes a critique after seeing all scores
      Round 3 — jurors revise after reading critique (parallel)

    Final score = weighted average of revised scores.
    Weights: accuracy 40%, relevance 35%, conciseness 25%.
    """

    WEIGHTS = {"accuracy": 0.40, "relevance": 0.35, "conciseness": 0.25}

    def __init__(self, model: str = ""):
        from config import LLM_MODEL
        self.model = model or LLM_MODEL

    async def evaluate(self, query: str, answer: str) -> JuryVerdict:
        round1 = await self._round1_independent(query, answer)
        critique_data = await self._round2_adversary(query, answer, round1)
        round3 = await self._round3_revise(query, answer, round1, critique_data.get("critique", ""))

        delta = sum(
            abs(round3[role]["revised_score"] - round1[role]["score"])
            for role in self.WEIGHTS
        ) / len(self.WEIGHTS)

        final = sum(
            round3[role]["revised_score"] * weight
            for role, weight in self.WEIGHTS.items()
        )

        return JuryVerdict(
            final_score=round(final, 2),
            accuracy=round3["accuracy"]["revised_score"],
            relevance=round3["relevance"]["revised_score"],
            conciseness=round3["conciseness"]["revised_score"],
            adversary_critique=critique_data.get("critique", "No critique generated."),
            score_delta=round(delta, 2),
            jurors_too_lenient=critique_data.get("jurors_too_lenient", False),
            model=self.model,
        )

    async def _round1_independent(self, query: str, answer: str) -> dict:
        prompts = {
            role: prompt.format(query=query, answer=answer)
            for role, prompt in _JUROR_PROMPTS.items()
        }
        responses = await asyncio.gather(*[
            llm_client.simple_prompt(p, max_tokens=300, model=self.model)
            for p in prompts.values()
        ])
        results = {}
        for role, response in zip(prompts.keys(), responses):
            data = self._parse_json(response) or {"score": 5, "reasoning": "parse failed"}
            results[role] = data
        return results

    async def _round2_adversary(self, query: str, answer: str, round1: dict) -> dict:
        prompt = _ADVERSARY_PROMPT.format(
            query=query,
            answer=answer,
            accuracy_score=round1["accuracy"].get("score", 5),
            accuracy_reasoning=round1["accuracy"].get("reasoning", ""),
            conciseness_score=round1["conciseness"].get("score", 5),
            conciseness_reasoning=round1["conciseness"].get("reasoning", ""),
            relevance_score=round1["relevance"].get("score", 5),
            relevance_reasoning=round1["relevance"].get("reasoning", ""),
        )
        response = await llm_client.simple_prompt(prompt, max_tokens=600, model=self.model)
        return self._parse_json(response) or {
            "critique": response[:500],
            "jurors_too_lenient": False,
        }

    async def _round3_revise(
        self, query: str, answer: str, round1: dict, critique: str
    ) -> dict:
        prompts = {
            role: _REVISION_PROMPT.format(
                query=query,
                answer=answer,
                original_score=round1[role].get("score", 5),
                original_reasoning=round1[role].get("reasoning", ""),
                critique=critique,
            )
            for role in self.WEIGHTS
        }
        responses = await asyncio.gather(*[
            llm_client.simple_prompt(p, max_tokens=250, model=self.model)
            for p in prompts.values()
        ])
        results = {}
        for role, response in zip(prompts.keys(), responses):
            data = self._parse_json(response)
            if data:
                results[role] = data
            else:
                results[role] = {
                    "revised_score": round1[role].get("score", 5),
                    "changed": False,
                    "justification": "parse failed — kept original",
                }
        return results

    @staticmethod
    def _parse_json(response: str) -> Optional[dict]:
        for fn in [
            lambda r: json.loads(r.strip()),
            lambda r: json.loads(re.sub(r'```(?:json)?\s*|\s*```', '', r).strip()),
            lambda r: json.loads(re.search(r'\{.*?\}', r, re.DOTALL).group(0)),
        ]:
            try:
                return fn(response)
            except Exception:
                pass
        return None
