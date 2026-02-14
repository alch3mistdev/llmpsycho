"""Example adaptive profiling run with Anthropic Claude API."""

from __future__ import annotations

import json

from adaptive_profiler import (
    AnthropicAdapter,
    AdaptiveProfilerEngine,
    RunConfig,
    build_item_bank,
)


def main() -> None:
    config = RunConfig(model_id="claude-3-5-sonnet")
    item_bank = build_item_bank(seed=17)

    adapter = AnthropicAdapter(
        model="claude-3-5-sonnet-20241022",
        max_tokens=80,
    )

    engine = AdaptiveProfilerEngine(config=config, item_bank=item_bank, seed=42)
    report = engine.run(adapter, run_id="anthropic-run")

    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
