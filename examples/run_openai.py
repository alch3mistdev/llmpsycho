"""Example adaptive profiling run with OpenAI API."""

from __future__ import annotations

import json

from adaptive_profiler import (
    OpenAIAdapter,
    AdaptiveProfilerEngine,
    RunConfig,
    build_item_bank,
)


def main() -> None:
    config = RunConfig(model_id="gpt-4o")
    item_bank = build_item_bank(seed=17)

    adapter = OpenAIAdapter(
        model="gpt-4o",
        max_tokens=80,
    )

    engine = AdaptiveProfilerEngine(config=config, item_bank=item_bank, seed=42)
    report = engine.run(adapter, run_id="openai-run")

    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
