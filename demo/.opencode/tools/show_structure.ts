// Stage tool: calls harness/tools.py (show_structure); the Python side also updates the stage panel.
import { tool } from "@opencode-ai/plugin"

import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")

export default tool({
  description: 'Show a protein structure in the 3D viewer, optionally highlighting a bound ligand (by residue name) and residues.',
  args: {
    pdb: tool.schema.string().describe('PDB ID, e.g. 1T46'),
    highlight_ligand: tool.schema.string().optional().describe('ligand residue name, e.g. STI for imatinib'),
    residues: tool.schema.array(tool.schema.number()).optional().describe('residue numbers to highlight'),
    caption: tool.schema.string().optional().describe('one-line caption'),
  },
  async execute(args) {
    const out = await Bun.$`${DEMO}/.venv/bin/python -m demo.harness.tools show_structure ${JSON.stringify(args)}`.cwd(ROOT).quiet().nothrow()
    return out.stdout.toString().trim() || out.stderr.toString().trim().slice(-800)
  },
})
