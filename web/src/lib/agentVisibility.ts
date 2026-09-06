import { agentRootName } from "@/lib/forkHarness";

/** Presentation-only filter for selectors that start sessions. Never filter
 * history or harness capabilities: composed agents can use a hidden agent's SDK.
 * Unset VITE_HIDDEN_AGENT_NAMES preserves upstream selection behavior.
 */
export function isAgentSelectable(name: string): boolean {
  const hidden = (import.meta.env.VITE_HIDDEN_AGENT_NAMES ?? "")
    .split(",")
    .map((entry: string) => entry.trim().toLowerCase())
    .filter(Boolean);
  return !hidden.includes(agentRootName(name.trim()).toLowerCase());
}
