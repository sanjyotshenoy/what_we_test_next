"""One bounded BYOK run. Secret arrives on stdin, never argv, disk or tool inputs.

Uses the shared LLM wrapper and the existing six validated demo tools. Unlike the
private OpenCode runtime, this process has no persistent provider/auth database.
"""
import json
import os
import resource
import subprocess
import sys

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


def emit(state, message):
    print(json.dumps({'state': state, 'message': message}), flush=True)


def tool(name, args, session):
    if name not in TOOLS or not isinstance(args, dict):
        return {'error': 'Unknown tool or invalid argument object'}
    pipeline = name in ('planning_submit', 'planning_simulate')
    python = DEMO / ('.venv/bin/python' if pipeline else '.venv-paperclip/bin/python')
    module = 'demo.harness.planning_pipeline' if pipeline else 'demo.harness.planning_evidence'
    completed = subprocess.run([str(python), '-m', module, name, json.dumps(args), session],
                               cwd=ROOT, capture_output=True, text=True, timeout=150)
    try:
        return json.loads(completed.stdout)
    except ValueError:
        return {'error': 'Tool failed; no usable result returned'}


def run(payload, chat, session):
    prompt = (DEMO / 'harness/stage/planner_prompt.md').read_text()
    prompt += '\nTransport: Return ONLY a JSON object, no markdown. To execute one tool use '
    prompt += '{"tool":"name","args":{...}}. To finish use {"done":true}. '
    prompt += 'Tool results are supplied as data in subsequent user messages. Available tools: ' + json.dumps(TOOLS)
    messages = [{'role': 'user', 'content': payload['question']}]
    for step in range(16):
        emit('running', f'Model turn {step + 1} of 16')
        response = chat(messages, model=payload['model'], system=prompt,
                        temperature=0, max_tokens=16384, timeout=120)
        try:
            action = json.loads(response)
        except (ValueError, TypeError):
            emit('failed', 'Model returned an invalid action. No automatic retry was made.')
            return
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
        emit('running', f'Running {name}')
        result = tool(name, args, session)
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
    llm.client().max_retries = 0
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
