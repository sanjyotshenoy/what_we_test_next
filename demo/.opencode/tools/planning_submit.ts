import { tool } from "@opencode-ai/plugin"
import { fromJSONSchema } from "zod"
import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")
const schema = JSON.parse(await Bun.file(`${DEMO}/harness/opencode/private/submission-schema.json`).text())
export default tool({
  description: "Validate and compile a cited experiment batch. Returns rejection reasons or a batch ID. Does not simulate or run hardware.",
  args: { batch: fromJSONSchema(schema).describe("Batch matching submission_schema from planning_context. Each proposal.citations must include proto:bacterial_mic_broth and every evidence_link citation.") },
  async execute(args, context) {
    const proc = Bun.spawn([`${DEMO}/.venv/bin/python`, "-m", "demo.harness.planning_pipeline",
      "planning_submit", JSON.stringify(args), context.sessionID],
      { cwd: ROOT, stdout: "pipe", stderr: "pipe", signal: context.abort, timeout: 45000 })
    const output = await new Response(proc.stdout).text()
    await proc.exited
    return output.trim() || JSON.stringify({ status: "error", error: "Pipeline tool failed or timed out" })
  },
})
