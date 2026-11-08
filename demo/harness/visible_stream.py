"""Adapt visible streamed completion content to wwtn.llm.chat's return contract.

Installed only inside one public worker. Never forwards provider reasoning fields,
request metadata, headers, or exceptions. No retries or simulated token playback.
"""
import time
from types import SimpleNamespace


def completion_bridge(create, publish):
    def complete(**kwargs):
        stream = create(**kwargs, stream=True)
        pieces, pending = [], ''
        last = time.monotonic()
        finished = False
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                text = choice.delta.content
                if isinstance(text, str) and text:
                    pieces.append(text); pending += text
                    if len(pending) >= 256 or time.monotonic() - last >= .1:
                        publish(pending); pending = ''; last = time.monotonic()
                if choice.finish_reason:
                    finished = choice.finish_reason == 'stop'
            if pending:
                publish(pending)
            if not finished:
                raise ValueError('Incomplete model output; no tool was executed')
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=''.join(pieces)))])
        finally:
            stream.close()
    return complete
