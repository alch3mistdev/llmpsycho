"""Run diagnostics, including benchmark-overfit detection."""

from __future__ import annotations

from collections import defaultdict
import statistics

from .types import ResponseRecord


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _z(x: float, scale: float = 0.20) -> float:
    scale = max(scale, 1e-6)
    return x / scale


def paraphrase_consistency(records: list[ResponseRecord], group_by_item: dict[str, str | None]) -> float:
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in records:
        group = group_by_item.get(record.item_id)
        if not group:
            continue
        grouped[group].append(record.score)

    if not grouped:
        return 1.0

    diffs: list[float] = []
    for vals in grouped.values():
        if len(vals) < 2:
            continue
        diffs.append(max(vals) - min(vals))

    if not diffs:
        return 1.0
    avg_diff = _mean(diffs)
    return max(0.0, min(1.0, 1.0 - avg_diff))


def benchmark_training_index(
    records: list[ResponseRecord],
    item_is_ood: dict[str, bool],
    item_is_sentinel: dict[str, bool],
) -> tuple[float, dict[str, float]]:
    """
    BTI combines in-bank vs paraphrase/OOD performance gaps and person-fit anomaly.
    """
    in_bank_scores: list[float] = []
    ood_scores: list[float] = []
    residuals: list[float] = []

    for record in records:
        residuals.append(abs(record.score - record.expected_probability))
        if item_is_ood.get(record.item_id, False):
            ood_scores.append(record.score)
            continue
        if item_is_sentinel.get(record.item_id, False):
            # Keep sentinels out of in-bank mean to avoid bias.
            continue
        in_bank_scores.append(record.score)

    in_bank = _mean(in_bank_scores)
    ood = _mean(ood_scores)
    person_fit_anomaly = _mean(residuals)

    bti = _z(in_bank - ood) + _z(person_fit_anomaly - 0.32)
    components = {
        "in_bank_mean": in_bank,
        "ood_mean": ood,
        "person_fit_anomaly": person_fit_anomaly,
    }
    return bti, components


def estimate_ood_gap(records: list[ResponseRecord], item_is_ood: dict[str, bool]) -> float:
    in_bank = [r.score for r in records if not item_is_ood.get(r.item_id, False)]
    ood = [r.score for r in records if item_is_ood.get(r.item_id, False)]
    return _mean(in_bank) - _mean(ood)


def summary_call_stats(records: list[ResponseRecord]) -> dict[str, float]:
    calls = len(records)
    if calls == 0:
        return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_ms_p50": 0.0}

    prompt = sum(r.prompt_tokens for r in records)
    completion = sum(r.completion_tokens for r in records)
    latencies = sorted(r.latency_ms for r in records)
    return {
        "calls": calls,
        "prompt_tokens": float(prompt),
        "completion_tokens": float(completion),
        "latency_ms_p50": float(statistics.median(latencies)),
    }
