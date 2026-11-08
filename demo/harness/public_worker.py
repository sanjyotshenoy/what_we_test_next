"""One bounded BYOK run. Secret arrives on stdin, never argv, disk or tool inputs.

Uses the shared LLM wrapper and the existing six validated demo tools. Unlike the
private OpenCode runtime, this process has no persistent provider/auth database.
"""
import json
import os
import resource
import subprocess
import sys
import threading

from demo.harness.paths import ROOT, DEMO

# TODO(final): Rehearse this public transport with a visitor-supplied Nebius key;
# isolation and tool dispatch are tested without paid inference.
TOOLS = {
    'planning_context': '{}',
    'biology_lookup': '{compound: string, species: string, limit?: integer 1..10}',
    'literature_search': '{query: string, limit?: integer 1..5}',
    'literature_read': '{paper_id: string, start?: integer, end?: integer (at most 60 lines)}',
    'planning_submit': '{batch: submission_schema returned by planning_context}',
    'planning_simulate': '{batch_id: accepted submission batch_id}',
}


STAGES = {'planning_context': 'context', 'biology_lookup': 'biology',
          'literature_search': 'literature', 'literature_read': 'literature',
          'planning_submit': 'checks', 'planning_simulate': 'simulation'}


def emit(state, message, **fields):
    print(json.dumps({'state': state, 'message': message, **fields}), flush=True)


def emit_output(text):
    for offset in range(0, len(text), 2048):
        emit('running', 'Receiving model output', kind='model_delta', stage='model', text=text[offset:offset+2048])


def tool(name, args, session):
    if name not in TOOLS or not isinstance(args, dict):
        return {'error': 'Unknown tool or invalid argument object'}
    pipeline = name in ('planning_submit', 'planning_simulate')
    python = DEMO / ('.venv/bin/python' if pipeline else '.venv-paperclip/bin/python')
    module = 'demo.harness.planning_pipeline' if pipeline else 'demo.harness.planning_evidence'
    result = {'error': 'Tool failed; no usable result returned'}
    with subprocess.Popen([str(python), '-m', module, name, json.dumps(args), session],
                          cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                          env={**os.environ, 'WWTN_PUBLIC_PROGRESS': '1'}) as process:
        timer = threading.Timer(150, process.kill)
        timer.start()
        try:
            for line in process.stdout:
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict) and value.get('_public_progress') in ('checks', 'protocols'):
                    stage = value['_public_progress']
                    emit('running', 'Checking design' if stage == 'checks' else 'Compiling protocols',
                         kind='stage', stage=stage)
                else:
                    result = value
            process.wait()
        finally:
            timer.cancel()
    return result


def run(payload, chat, session):
    prompt = (DEMO / 'harness/stage/planner_prompt.md').read_text()
    prompt += '\nTransport: Return ONLY a JSON object, no markdown. To execute one tool use '
    prompt += '{"tool":"name","args":{...}}. To finish use {"done":true}. '
    prompt += 'Tool results are supplied as data in subsequent user messages. Available tools: ' + json.dumps(TOOLS)
    messages = [{'role': 'user', 'content': payload['question']}]
    for step in range(16):
        emit('running', f'Model turn {step + 1} of 16', kind='model_start', stage='model', turn=step+1)
        response = chat(messages, model=payload['model'], system=prompt,
                        temperature=0, max_tokens=16384, timeout=120)
        try:
            action = json.loads(response)
        except (ValueError, TypeError):
            emit('failed', 'Model returned an invalid action. No automatic retry was made.')
            return
        emit('running', 'Model output complete', kind='model_end', stage='model', turn=step+1)
        if not isinstance(action, dict):
            emit('failed', 'Model returned an invalid action.')
            return
        if action.get('done') is True:
            emit('finished', 'Planning stopped. Inspect the artifacts and verified simulation status below.')
            return
        name, args = action.get('tool'), action.get('args')
        if name not in TOOLS or not isinstance(args, dict):
            emit('failed', 'Model requested an unsupported action.')
            return
        if name == 'planning_submit':
            emit('running', 'Draft proposal ready for checks', kind='proposal', stage='proposal')
        inputs = json.dumps(args, ensure_ascii=False, indent=2)
        emit('running', f'Running {name}', kind='tool_start', stage=STAGES[name], tool=name,
             text=inputs[:6000], truncated=len(inputs)>6000)
        result = tool(name, args, session)
        failed = not isinstance(result, dict) or bool(result.get('error')) or result.get('status') in ('rejected', 'error', 'failed', 'simulation_incomplete')
        preview = json.dumps(result, ensure_ascii=False, indent=2)
        emit('running', f'{name} returned', kind='tool_result', tool=name,
             stage=STAGES[name], outcome='failed' if failed else 'returned',
             text=preview[:6000], truncated=len(preview)>6000)
        messages.extend([{'role': 'assistant', 'content': response},
                         {'role': 'user', 'content': json.dumps({'tool': name, 'result': result})}])
        if name == 'planning_simulate':
            emit('finished' if result.get('status') == 'simulated' else 'failed',
                 'Simulation finished; inspect the verified reports.' if result.get('status') == 'simulated'
                 else 'Simulation did not complete. Review the available artifacts.')
            return
    emit('failed', 'The 16-turn limit was reached. Review the available artifacts.')


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    payload = json.loads(sys.stdin.readline())
    key = payload.pop('key')
    if not isinstance(key, str) or not key.strip():
        raise ValueError('A supplied key is required')
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    os.environ['NEBIUS_BASE_URL'] = 'https://api.tokenfactory.nebius.com/v1/'
    os.environ['NEBIUS_API_KEY'] = key
    from wwtn import llm
    # Initialize only this process's client, then remove the key from child envs.
    client = llm.client()
    client.max_retries = 0
    from demo.harness.visible_stream import completion_bridge
    client.chat.completions.create = completion_bridge(
        client.chat.completions.create,
        emit_output)
    os.environ.pop('NEBIUS_API_KEY', None)
    del key
    run(payload, llm.chat, sys.argv[1])


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Provider exceptions can contain headers/transport details. Never echo them.
        emit('failed', 'The run stopped: check your key, model access, or retrieval availability.')
        sys.exit(1)
