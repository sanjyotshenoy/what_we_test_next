import { tool } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")
export default tool({
  description: "Simulate compiled OT-2 runs for this session. No hardware execution. Stops on first failure.",
  args: { batch_id: tool.schema.string().regex(/^[a-f0-9]{16}$/) },
  async execute(args, context) {
    const proc = Bun.spawn([`${DEMO}/.venv/bin/python`, "-m", "demo.harness.planning_pipeline",
      "planning_simulate", JSON.stringify(args), context.sessionID],
      { cwd: ROOT, stdout: "pipe", stderr: "pipe", signal: context.abort, timeout: 780000 })
    const output = await new Response(proc.stdout).text()
    await proc.exited
    return output.trim() || JSON.stringify({ status: "error", error: "Pipeline tool failed or timed out" })
  },
})
