import { tool } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")
export default tool({
  description: "Read a bounded paper passage with metadata and an evidence ID for citations.",
  args: { paper_id: tool.schema.string(), start: tool.schema.number().int().min(1).default(1), end: tool.schema.number().int().min(1).default(30) },
  async execute(args, context) {
    const proc = Bun.spawn([`${DEMO}/.venv-paperclip/bin/python`, "-m", "demo.harness.planning_evidence",
      "literature_read", JSON.stringify(args), context.sessionID],
      { cwd: ROOT, stdout: "pipe", stderr: "pipe", signal: context.abort, timeout: 45000 })
    const output = await new Response(proc.stdout).text()
    await proc.exited
    return output.trim() || JSON.stringify({ error: "Evidence tool failed or timed out; no result recorded" })
  },
})
