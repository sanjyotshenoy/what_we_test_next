"""Run the actual provider stream adapter in Chromium's JS runtime (no Node needed)."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright


class StreamTests(unittest.TestCase):
    def test_stream_contract(self):
        source = (Path(__file__).resolve().parents[1] / '.opencode/providers/tool-stream.mjs').read_text()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            try:
                page = browser.new_page()
                page.route('https://stream.test/', lambda route: route.fulfill(body='<html></html>'))
                page.goto('https://stream.test/')
                count = page.evaluate('async () => {' + source.replace('export ', '') + r'''
const assert = (x, msg) => { if (!x) throw Error(msg) }
const event = (calls, finish = null) => ({choices: [{index: 0, delta: {tool_calls: calls}, finish_reason: finish}]})
let n = 0
for (const id of ['call_ok', 47, null]) {
  const s = new ToolStream()
  const first = s.consume(event([{index: 0, id, function: {name:'lookup', arguments:'{"q":'}}]))
  assert(!first.choices[0].delta.tool_calls, 'early incomplete call escaped')
  s.consume(event([{function: {arguments:'"hello"}'}}]))
  const call = s.consume(event([], 'tool_calls')).choices[0].delta.tool_calls[0]
  assert(typeof call.id === 'string' && call.id.length > 0, 'missing ID')
  assert(call.function.arguments === '{"q":"hello"}', 'arguments changed')
  assert(call.function.name === 'lookup', 'name changed'); s.done(); n++
}
const late = new ToolStream()
late.consume(event([{function:{arguments:'{}'}}]))
late.consume(event([{id:'late', function:{name:'lookup'}}]))
assert(late.consume(event([], 'tool_calls')).choices[0].delta.tool_calls.length === 1, 'late metadata split call'); n++
const multi = new ToolStream()
multi.consume(event([{index:0,id:'a',function:{name:'a',arguments:'{'}},{index:1,id:'b',function:{name:'b',arguments:'['}}]))
multi.consume(event([{index:1,function:{arguments:']'}},{index:0,function:{arguments:'}'}}]))
assert(multi.consume(event([], 'tool_calls')).choices[0].delta.tool_calls[1].function.arguments === '[]', 'mixed parallel args'); n++
const mustThrow = fn => {let threw=false; try { fn() } catch { threw=true }; assert(threw, 'should reject malformed stream'); n++}
mustThrow(() => {const s=new ToolStream(); s.consume(event([{index:0,function:{name:'a',arguments:'{}'}}])); s.done()})
mustThrow(() => {const s=new ToolStream(); s.consume(event([{index:0,function:{arguments:'{}'}}])); s.consume(event([], 'tool_calls'))})
mustThrow(() => {const s=new ToolStream(); s.consume(event([{index:0,id:'a'},{index:1,id:'b'}])); s.consume(event([{function:{arguments:'{}'}}]))})
mustThrow(() => {const s=new ToolStream(); s.consume(event([{index:0,id:'a'}])); s.consume(event([{index:0,id:'b'}]))})
const chunks = [event([{index:0,id:9,function:{name:'lookup',arguments:'{"q":"β"}'}}]),
 {choices:[{index:0,delta:{content:'visible text'},finish_reason:'tool_calls'}],usage:{total_tokens:5}}]
const wire = chunks.map(x => 'data: '+JSON.stringify(x)+'\r\n\r\n').join('')+'data: [DONE]\r\n\r\n'
const bytes=new TextEncoder().encode(wire)
const body=new ReadableStream({start(c){for (const b of bytes) c.enqueue(new Uint8Array([b])); c.close()}})
const text=await normalizeToolResponse(new Response(body,{headers:{'content-type':'text/event-stream'}})).text()
assert(text.includes('β') && text.includes('visible text') && text.includes('total_tokens'), 'SSE damaged text or usage'); n++
let failed=false
try {await normalizeToolResponse(new Response('data: '+JSON.stringify(event([{id:'x',function:{name:'a',arguments:'{}'}}]))+'\n\n', {headers:{'content-type':'text/event-stream'}})).text()} catch {failed=true}
assert(failed,'truncated stream was accepted'); n++
const empty=new ToolStream(); empty.consume(event([{index:0,function:{arguments:''}}]))
assert(!empty.consume(event([], 'stop')).choices[0].delta.tool_calls,'empty placeholder became tool call'); n++
return n
}''')
                self.assertEqual(count, 12)
            finally:
                browser.close()

    def test_complete_response_contract(self):
        source = (Path(__file__).resolve().parents[1] / '.opencode/providers/tool-stream.mjs').read_text()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            try:
                page = browser.new_page()
                page.route('https://stream.test/', lambda route: route.fulfill(body='<html></html>'))
                page.goto('https://stream.test/')
                page.evaluate('async () => {' + source.replace('export ', '') + r'''
const assert=(x,m)=>{if(!x)throw Error(m)}
const init={body:JSON.stringify({stream:true,stream_options:{include_usage:true}}), signal:new AbortController().signal}
const message=(id)=>({choices:[{index:0,message:{content:'answer',tool_calls:[{id,type:'function',function:{name:'lookup',arguments:'{"q":"β"}'}}]},finish_reason:'tool_calls'}],usage:{total_tokens:7}})
for(const id of ['valid',19,null]){
 let calls=0
 const response=await completeToolResponse(async(url,request)=>{
   calls++;assert(request.signal===init.signal,'abort signal lost')
   const body=JSON.parse(request.body);assert(body.stream===false&&!body.stream_options,'not complete transport')
   return Response.json(message(id))
 },'https://example.invalid',init)
 const wire=await response.text();const data=JSON.parse(wire.split('\n')[0].slice(6))
 const call=data.choices[0].delta.tool_calls[0]
 assert(typeof call.id==='string'&&call.id.length>0,'invalid normalized ID')
 assert(call.function.arguments==='{"q":"β"}'&&data.usage.total_tokens===7,'payload changed')
 assert(calls===1&&wire.endsWith('data: [DONE]\n\n'),'retry or malformed SSE')
}
for(const mutate of [d=>delete d.choices,d=>d.choices=[],d=>delete d.choices[0].message,
 d=>d.choices[0].message.tool_calls[0].function.name='',
 d=>d.choices[0].message.tool_calls[0].function.arguments='{',
 d=>d.choices[0].message.tool_calls[0].function.arguments='null',
 d=>d.choices[0].message.tool_calls[0].function.arguments='[]',
 d=>{d.choices[0].message.tool_calls=[];d.choices[0].finish_reason='length'},
 d=>d.choices[0].finish_reason='length']){
 let data=message('a');mutate(data);let failed=false
 try{await completeToolResponse(async()=>Response.json(data),'url',init)}catch{failed=true}
 assert(failed,'malformed response accepted')
}
const error=new Response('rate limited',{status:429})
assert(await completeToolResponse(async()=>error,'url',init)===error,'upstream error replaced')
let cancelled=false
try{await completeToolResponse(async()=>{throw new DOMException('aborted','AbortError')},'url',init)}catch(e){cancelled=e.name==='AbortError'}
assert(cancelled,'cancellation swallowed')
const direct={body:JSON.stringify({stream:false})};const response=new Response('direct')
assert(await completeToolResponse(async(u,i)=>{assert(i===direct,'nonstream request changed');return response},'url',direct)===response,'nonstream response changed')
''' + '}')
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
