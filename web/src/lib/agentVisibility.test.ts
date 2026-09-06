import { afterEach, describe, expect, it, vi } from "vitest";
import { isAgentSelectable } from "./agentVisibility";

afterEach(() => vi.unstubAllEnvs());

describe("agent selection visibility", () => {
  it("is opt-in", () => {
    vi.stubEnv("VITE_HIDDEN_AGENT_NAMES", "");
    expect(isAgentSelectable("homelab-observer")).toBe(true);
    expect(isAgentSelectable("claude-sdk")).toBe(true);
  });

  it("matches exact root names, including nested fork/switch clones", () => {
    vi.stubEnv("VITE_HIDDEN_AGENT_NAMES", " homelab-observer, homelab-engineer, CLAUDE-SDK, ");
    for (const name of ["homelab-observer", "Homelab-engineer", "claude-sdk"]) {
      expect(isAgentSelectable(name)).toBe(false);
      expect(isAgentSelectable(`${name} (fork ag_a) (switch ag_b)`)).toBe(false);
    }
    for (const name of [
      "polly",
      "debby",
      "claude-native-ui",
      "codex-native-ui",
      "cursor-native-ui",
      "pi-native-ui",
      "my-claude-sdk",
      "homelab-observer-notes",
    ]) {
      expect(isAgentSelectable(name)).toBe(true);
    }
  });
});
