# Tests for compaction-gate plugin
# Hook is on_pre_compress(session_id, turn_count, ..., agent=); fail-open; returns None.
import json, sys, importlib.util, tempfile, os
from pathlib import Path
from types import SimpleNamespace


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        'compaction_gate',
        Path(__file__).parent.parent / '__init__.py'
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['compaction_gate'] = mod
    spec.loader.exec_module(mod)
    return mod


def _hook(mod):
    return getattr(mod, 'on_pre_compress', None) or getattr(mod, 'pre_compress', None)


def _agent(messages, session_id='t'):
    return SimpleNamespace(conversation_history=messages, session_id=session_id)


def test_depth_gate_below_threshold():
    # Below default depth_threshold (50): hook returns None (observability skip, allow compression)
    mod = load_plugin()
    fn = _hook(mod)
    ctx_msgs = []
    result = fn(session_id='t', turn_count=10, agent=_agent(ctx_msgs))
    assert result is None or result == {} or result is True, f'Expected allow below threshold, got {result}'


def test_depth_gate_above_threshold():
    # Above threshold: hook fires (extracts/scores facts) and must not raise
    mod = load_plugin()
    fn = _hook(mod)
    msgs = [{'role': 'user', 'content': 'x' * 40} for _ in range(100)]
    try:
        fn(session_id='t', turn_count=100, agent=_agent(msgs))
    except Exception as e:
        assert False, f'on_pre_compress raised: {e}'


def test_fail_open():
    # Even with bad input, hook must not raise
    mod = load_plugin()
    fn = _hook(mod)
    try:
        fn(None)
        fn(session_id='', turn_count=0, agent=None)
        fn(session_id='t', turn_count='bad', agent=object())
    except Exception as e:
        assert False, f'fail-open violated: {e}'


def test_mdl_redundancy():
    # MDL scorer should assign identical facts the same saving
    mod = load_plugin()
    if hasattr(mod, '_mdl_score'):
        facts = ['The sky is blue.', 'The sky is blue.', 'Different fact here.']
        scores = [mod._mdl_score(f, facts) for f in facts]
        assert scores[0] == scores[1], 'Identical facts should have same MDL score'
        return
    if not hasattr(mod, '_score_facts'):
        return  # optional
    facts = [
        'The sky is blue and the ocean is also quite blue today.',
        'The sky is blue and the ocean is also quite blue today.',
        'Different fact here about a unique file path /tmp/abc.',
    ]
    scored, _flagged = mod._score_facts(facts, 0.1)
    assert len(scored) >= 2, f'expected scored facts, got {scored}'
    assert scored[0]['mdl_saving'] == scored[1]['mdl_saving'], (
        'Identical facts should have same MDL score'
    )


if __name__ == '__main__':
    test_depth_gate_below_threshold()
    test_depth_gate_above_threshold()
    test_fail_open()
    test_mdl_redundancy()
    print('All tests PASS')
