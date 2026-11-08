// Stage tool: calls harness/tools.py (kg_search); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: 'Search the biology/protocol knowledge graph by name or ID. Returns matching nodes with their IDs. Highlights them on screen.',
  args: {
    query: tool.schema.string().describe('compound, target, class or protocol name, or an ID such as CHEMBL941'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools kg_search ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
