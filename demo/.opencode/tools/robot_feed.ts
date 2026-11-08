// Stage tool: calls harness/tools.py (robot_feed); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: 'Start, pause or reset the OT-2 run panel (the recorded robot run and its live status feed).',
  args: {
    action: tool.schema.string().describe('play | pause | reset'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools robot_feed ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
