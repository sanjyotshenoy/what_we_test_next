"""Adapt visible streamed completion content to wwtn.llm.chat's return contract.

Installed only inside one public worker. Provider-exposed reasoning is forwarded
only to an explicit separate callback. Never forwards request metadata, headers, or exceptions. No retries or simulated token playback.
"""
import time
from types import SimpleNamespace


def completion_bridge(create, publish, publish_reasoning=None):
    def complete(**kwargs):
        stream = create(**kwargs, stream=True)
        pieces, pending, pending_reasoning = [], '', ''
        last_reasoning = time.monotonic()
        last = time.monotonic()
        finished = False
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if publish_reasoning is not None:
                    extra = getattr(choice.delta, 'model_extra', None) or {}
                    if not isinstance(extra, dict):
                        extra = {}
                    for field in ('reasoning_content', 'reasoning'):
                        reasoning = getattr(choice.delta, field, None) or extra.get(field)
                        if isinstance(reasoning, str) and reasoning:
                            pending_reasoning += reasoning
                            if len(pending_reasoning) >= 256 or time.monotonic() - last_reasoning >= .1:
                                publish_reasoning(pending_reasoning); pending_reasoning = ''; last_reasoning = time.monotonic()
                            break
                text = choice.delta.content
                if isinstance(text, str) and text:
                    if pending_reasoning:
                        publish_reasoning(pending_reasoning); pending_reasoning = ''
                    pieces.append(text); pending += text
                    if len(pending) >= 256 or time.monotonic() - last >= .1:
                        publish(pending); pending = ''; last = time.monotonic()
                if choice.finish_reason:
                    finished = choice.finish_reason == 'stop'
            if pending_reasoning:
                publish_reasoning(pending_reasoning)
            if pending:
                publish(pending)
            if not finished:
                raise ValueError('Incomplete model output; no tool was executed')
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=''.join(pieces)))])
        finally:
            stream.close()
    return complete
