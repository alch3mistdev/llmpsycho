"""Trait definitions and defaults for LLM profiling."""

from __future__ import annotations

TRAITS: tuple[tuple[str, str], ...] = (
    ("T1", "Analytic Accuracy"),
    ("T2", "Reasoning Stability"),
    ("T3", "Instruction and Format Control"),
    ("T4", "Epistemic Calibration"),
    ("T5", "Intent Understanding"),
    ("T6", "Grounded Truthfulness"),
    ("T7", "Consistency and Drift Resistance"),
    ("T8", "Refusal Correctness"),
    ("T9", "Jailbreak Robustness"),
    ("T10", "Safe Helpfulness"),
    ("T11", "Paraphrase and OOD Invariance"),
    ("T12", "Tool Discipline"),
)

TRAIT_CODES: tuple[str, ...] = tuple(code for code, _ in TRAITS)
TRAIT_NAMES: dict[str, str] = {code: name for code, name in TRAITS}
TRAIT_INDEX: dict[str, int] = {code: idx for idx, code in enumerate(TRAIT_CODES)}

CRITICAL_TRAITS_DEFAULT: tuple[str, ...] = ("T4", "T5", "T8", "T9", "T10")

REGIME_DEPENDENT_TRAITS: tuple[str, ...] = (
    "T3",
    "T4",
    "T5",
    "T6",
    "T8",
    "T9",
    "T10",
    "T12",
)
