import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { InfoTooltip } from "./InfoTooltip";
import { useStudioStore } from "../store/useStudioStore";
import { renderWithProviders } from "../test/test-utils";

describe("InfoTooltip", () => {
  it("shows explanatory content and can pin it", async () => {
    const user = userEvent.setup();
    useStudioStore.setState({ pinnedTooltip: null });

    renderWithProviders(
      <InfoTooltip
        id="intent"
        title="Intent Coverage"
        definition="Measures overlap between request and response intent tokens."
        whyItMatters="Low intent coverage signals a missed user objective."
        decisionImplication="Investigate intervention strategy."
      >
        <button type="button">Intent Coverage</button>
      </InfoTooltip>
    );

    await user.hover(screen.getByRole("button", { name: "Intent Coverage" }));
    expect(screen.getByText("Measures overlap between request and response intent tokens.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Pin" }));
    expect(useStudioStore.getState().pinnedTooltip?.id).toBe("intent");
  });
});
