import { completeToolResponse } from './tool-stream.mjs'
const { createOpenAICompatible } = await import('@ai-sdk/openai-compatible')

export function createNebiusCompatible(options) {
  const upstream = options.fetch || fetch
  return createOpenAICompatible({
    includeUsage: true,
    ...options,
    fetch: async (url, init) => completeToolResponse(upstream, url, init,
      reason => console.error('[nebius-stream] ' + reason)),
  })
}
