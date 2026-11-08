// Stage tool: calls harness/tools.py (kg_neighbors); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: "List a knowledge-graph node's neighbours (relation, direction, node). Use to find a target's class, compounds with measured activity on it, similar compounds, protocols for a class. Highlights the neighbourhood on screen.",
  args: {
    id: tool.schema.string().describe('node ID from kg_search'),
    rel: tool.schema.string().optional().describe('optional relation filter, e.g. HAS_ACTIVITY, SIMILAR_TO, MEMBER_OF, APPLICABLE_TO'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools kg_neighbors ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
