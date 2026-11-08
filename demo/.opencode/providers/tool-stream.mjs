// Compatibility boundary for AI SDK 2.0.41: that parser requires ID + name on
// the FIRST tool fragment. Buffer tool fragments until the choice finishes;
// forward text/reasoning/usage without changing them. Never invent arguments.
export class ToolStream {
  constructor(onRepair = () => {}) {
    this.choices = new Map()
    this.onRepair = onRepair
  }
  consume(event) {
    for (const choice of event.choices || []) {
      const key = choice.index ?? 0
      let calls = this.choices.get(key)
      if (!calls) this.choices.set(key, calls = new Map())
      const fragments = choice.delta?.tool_calls || []
      for (const fragment of fragments) {
        // Some endpoints emit an empty tool_calls placeholder during text turns.
        // It carries no call metadata or argument bytes and must not become a call.
        if (fragment.id == null && !fragment.function?.name && !fragment.function?.arguments) {
          this.onRepair('empty_fragment')
          continue
        }
        const id = fragment.id == null ? null : String(fragment.id)
        let index = fragment.index
        if (index == null) {
          const existing = id && [...calls.entries()].find(([, call]) => call.id === id)
          if (existing) index = existing[0]
          else if (id && calls.size === 1 && !calls.values().next().value.id) index = calls.keys().next().value
          else if (id) index = calls.size
          else if (calls.size <= 1) index = calls.size ? calls.keys().next().value : 0
          else throw new Error('Ambiguous tool fragment without index or ID')
          this.onRepair('missing_index')
        }
        if (!Number.isInteger(index) || index < 0) throw new Error('Invalid tool index')
        let call = calls.get(index)
        if (!call) {
          call = { index, id: null, type: 'function', function: { name: '', arguments: '' } }
          calls.set(index, call)
          if (!id) this.onRepair('missing_initial_id')
          if (!fragment.function?.name) this.onRepair('missing_initial_name')
        }
        if (id) {
          if (call.id && call.id !== id) throw new Error('Conflicting IDs for one tool index')
          call.id = id
          if (typeof fragment.id !== 'string') this.onRepair('numeric_id')
        }
        if (fragment.function?.name) call.function.name += fragment.function.name
        if (fragment.function?.arguments != null) call.function.arguments += fragment.function.arguments
        if (call.function.arguments.length > 512000) throw new Error('Tool arguments exceed compatibility limit')
        if (fragment.extra_content) call.extra_content = fragment.extra_content
      }
      if (choice.delta) delete choice.delta.tool_calls
      if (choice.finish_reason != null) {
        if (calls.size) {
          choice.delta ||= {}
          choice.delta.tool_calls = [...calls.values()].map(call => {
            if (!call.function.name) throw new Error(`Tool stream ended without a function name (${call.function.arguments.length} argument characters; finish=${choice.finish_reason})`)
            if (!call.id) {
              call.id = 'call_' + crypto.randomUUID().replaceAll('-', '')
              this.onRepair('generated_id')
            }
            return call
          })
        }
        this.choices.delete(key)
      }
    }
    return event
  }
  done() {
    if ([...this.choices.values()].some(calls => calls.size)) {
      throw new Error('Incomplete upstream tool stream: no finish marker')
    }
  }
}

export function normalizeToolResponse(response, onRepair) {
  if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('text/event-stream')) return response
  const state = new ToolStream(onRepair)
  const decoder = new TextDecoder(), encoder = new TextEncoder()
  let buffer = '', completed = false
  const emit = (frame, controller) => {
    const data = frame.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart()).join('\n')
    if (!data) { controller.enqueue(encoder.encode(frame + '\n\n')); return }
    if (data === '[DONE]') {
      state.done(); completed = true
      controller.enqueue(encoder.encode('data: [DONE]\n\n')); return
    }
    controller.enqueue(encoder.encode('data: ' + JSON.stringify(state.consume(JSON.parse(data))) + '\n\n'))
  }
  const body = response.body.pipeThrough(new TransformStream({
    transform(chunk, controller) {
      buffer += decoder.decode(chunk, { stream: true })
      buffer = buffer.replaceAll('\r\n', '\n')
      let index
      while ((index = buffer.indexOf('\n\n')) >= 0) {
        emit(buffer.slice(0, index), controller); buffer = buffer.slice(index + 2)
      }
      if (buffer.length > 2000000) throw new Error('Upstream SSE frame exceeds limit')
    },
    flush(controller) {
      buffer += decoder.decode()
      if (buffer.trim()) emit(buffer, controller)
      state.done()
      if (!completed) throw new Error('Upstream SSE stream ended before DONE')
    },
  }))
  const headers = new Headers(response.headers)
  headers.delete('content-length'); headers.delete('content-encoding')
  return new Response(body, { status: response.status, headers })
}

// Nebius/gpt-oss can omit BOTH ID and function name from an entire streamed
// call, not just its first chunk. Those bytes cannot be recovered safely.
// Request a complete response once, then adapt it to the SDK's SSE interface.
// This is a transport choice, not a model retry or a substitute agent loop.
export async function completeToolResponse(upstream, url, init, onRepair = () => {}) {
  const request = JSON.parse(init.body)
  if (!request.stream) return upstream(url, init)
  request.stream = false
  delete request.stream_options
  const response = await upstream(url, { ...init, body: JSON.stringify(request) })
  if (!response.ok) return response
  const data = await response.json()
  if (!Array.isArray(data.choices) || data.choices.length === 0) throw new Error("Missing response choices")
  for (const choice of data.choices) {
    if (!choice.message || !choice.finish_reason) throw new Error("Incomplete response choice")
    const message = choice.message || {}
    const calls = message.tool_calls || []
    if (calls.length && choice.finish_reason !== 'tool_calls' && choice.finish_reason !== 'stop') {
      throw new Error('Incomplete tool response: ' + choice.finish_reason)
    }
    for (const [index, call] of calls.entries()) {
      if (!call.function?.name || typeof call.function.arguments !== 'string') {
        throw new Error('Complete tool response is missing function name or arguments')
      }
      // Reject invalid arguments before any execution; never expose their contents.
      let args
      try { args = JSON.parse(call.function.arguments) }
      catch { throw new Error('Model returned malformed tool-call JSON; tool execution was blocked') }
      if (!args || typeof args !== 'object' || Array.isArray(args)) {
        throw new Error('Model tool arguments must be a JSON object; tool execution was blocked')
      }
      call.index = index
      if (call.id == null || call.id === '') {
        call.id = 'call_' + crypto.randomUUID().replaceAll('-', '')
        onRepair('generated_id')
      } else if (typeof call.id !== 'string') {
        call.id = String(call.id)
        onRepair('numeric_id')
      }
    }
    choice.delta = message
    delete choice.message
  }
  return new Response('data: ' + JSON.stringify(data) + '\n\ndata: [DONE]\n\n', {
    status: response.status, headers: { 'content-type': 'text/event-stream' },
  })
}
