// Stage tool: calls harness/tools.py (kg_annotate); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: "Pin a short note onto knowledge-graph nodes on the audience's screen. Use kind 'gap' for what the KB does not know, 'evidence' for supporting facts, 'proposal' for the experiment you propose.",
  args: {
    ids: tool.schema.array(tool.schema.string()).describe('node IDs to attach the note to'),
    note: tool.schema.string().describe('one short sentence'),
    kind: tool.schema.string().optional().describe('note | gap | evidence | proposal'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools kg_annotate ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
