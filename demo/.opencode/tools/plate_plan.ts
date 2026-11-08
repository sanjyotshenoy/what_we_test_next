// Stage tool: calls harness/tools.py (plate_plan); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: 'Lay out the proposed dose-response on the 96-well plate panel: concentration per column (serial dilution), rows as replicates, control columns.',
  args: {
    top_uM: tool.schema.number().describe('top concentration in µM (column 1)'),
    factor: tool.schema.number().describe('dilution factor between columns, e.g. 2 or 3'),
    n_points: tool.schema.number().optional().describe('number of concentrations (default 10)'),
    replicates: tool.schema.number().optional().describe('rows used, 1-8 (default 8)'),
    controls: tool.schema.record(tool.schema.string(), tool.schema.string()).optional().describe('map of column number to control name, e.g. {"11":"vehicle","12":"positive control"}'),
    title: tool.schema.string().optional().describe('short label'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools plate_plan ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
