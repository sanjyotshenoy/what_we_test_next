import { tool } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")
export default tool({
  description: "Resolve exact compound/species IDs or names in the bacterial MIC graph. Returns raw censored measurements with provenance; demo only.",
  args: { compound: tool.schema.string(), species: tool.schema.string(), limit: tool.schema.number().int().min(1).max(20).default(10) },
  async execute(args, context) {
    const proc = Bun.spawn([`${DEMO}/.venv-paperclip/bin/python`, "-m", "demo.harness.planning_evidence",
      "biology_lookup", JSON.stringify(args), context.sessionID],
      { cwd: ROOT, stdout: "pipe", stderr: "pipe", signal: context.abort, timeout: 45000 })
    const output = await new Response(proc.stdout).text()
    await proc.exited
    return output.trim() || JSON.stringify({ error: "Evidence tool failed or timed out; no result recorded" })
  },
})
