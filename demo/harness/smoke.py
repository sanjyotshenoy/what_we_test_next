"""Explicit direct-backend synthetic smoke test; never claims agent autonomy."""
import argparse
import json
import uuid
from demo.harness import planning_pipeline as pipeline
from demo.harness import planning_evidence as evidence
from demo.harness.test_planning_pipeline import fixture_batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_args()
    session = 'direct-fixture-' + uuid.uuid4().hex[:12]
    evidence.run('planning_context', {}, session)
    result = pipeline.submit(fixture_batch(2, 2), session)
    assert result['status'] == 'compiled', result
    if args.simulate:
        result = pipeline.simulate_batch(result['batch_id'], session)
        assert result['status'] == 'simulated', result
    print(json.dumps({'session':session, 'provenance':'direct backend synthetic software fixture; not an autonomous agent run', 'result':result},indent=2))


if __name__ == '__main__':
    main()
