// ShipLoop keepalive for OpenCode. `shiploop-hook install --host opencode`
// writes this file, with the hook path filled in, to the global plugins folder.
// It binds a session to a run from shell output and, when the session goes
// idle while the run is still active, sends the run's next command as the
// next message. `opencode run` exits before answering it; shiploop-drive
// resumes that session instead.
import { spawnSync } from "node:child_process";

const HOOK = __SHIPLOOP_HOOK__;

function hook(event, payload) {
  const result = spawnSync("python3", [HOOK, event, "--host", "opencode"], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 30000,
  });
  return (result.stdout || "").trim();
}

export const ShipLoopKeepalive = async ({ client }) => ({
  "tool.execute.after": async (input, output) => {
    hook("observe", { sessionID: input.sessionID, tool: input.tool, output: String(output?.output ?? "") });
  },
  event: async ({ event }) => {
    if (event.type !== "session.idle") return;
    const sessionID = event.properties.sessionID;
    const reply = hook("stop", { sessionID });
    if (!reply) return;
    let message;
    try {
      message = JSON.parse(reply).followup_message;
    } catch {
      return;
    }
    if (!message) return;
    await client.session.promptAsync({ path: { id: sessionID }, body: { parts: [{ type: "text", text: message }] } });
  },
});
