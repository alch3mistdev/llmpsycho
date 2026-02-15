import { act } from "@testing-library/react";
import { vi } from "vitest";

import { GuidedTourController } from "./GuidedTourController";
import { renderWithProviders } from "../test/test-utils";

const startMock = vi.fn();

vi.mock("shepherd.js", () => {
  class MockTour {
    steps: Array<{ isOpen: () => boolean }> = [{ isOpen: () => true }];
    on() {
      return this;
    }
    addStep() {
      return this;
    }
    next() {
      return this;
    }
    back() {
      return this;
    }
    complete() {
      return this;
    }
    start() {
      startMock();
      return this;
    }
  }
  return { default: { Tour: MockTour } };
});

describe("GuidedTourController", () => {
  it("starts the guided tour when the launcher event is dispatched", () => {
    renderWithProviders(<GuidedTourController />);
    act(() => {
      window.dispatchEvent(new Event("studio:start-tour"));
    });
    expect(startMock).toHaveBeenCalledTimes(1);
  });
});
