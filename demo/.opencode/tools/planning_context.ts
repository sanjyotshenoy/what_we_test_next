import { tool } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"
const DEMO = fileURLToPath(new URL("../../", import.meta.url)).replace(/\/$/, "")
const ROOT = fileURLToPath(new URL("../../../", import.meta.url)).replace(/\/$/, "")
export default tool({
  description: "Read the real team MIC template, source observations and lab capabilities. Not execution approval.",
  args: {  },
  async execute(args, context) {
    const proc = Bun.spawn([`${DEMO}/.venv-paperclip/bin/python`, "-m", "demo.harness.planning_evidence",
      "planning_context", JSON.stringify(args), context.sessionID],
      { cwd: ROOT, stdout: "pipe", stderr: "pipe", signal: context.abort, timeout: 45000 })
    const output = await new Response(proc.stdout).text()
    await proc.exited
    return output.trim() || JSON.stringify({ error: "Evidence tool failed or timed out; no result recorded" })
  },
})
