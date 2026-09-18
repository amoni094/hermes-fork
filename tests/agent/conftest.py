"""Agent-test conftest — shared fixtures for tests/agent/.

N6 fix: redirect HERMES_HOME to a temp dir so tests never touch ~/.hermes/.
Without this, SessionDB and _hint_path() in the lambda-tuner plugin write to
the live home, making tests non-hermetic and destructive.
"""
from __future__ import annotations

import os
import pytest


@pytest.fixture(autouse=True)
def isolated_hermes_home(tmp_path, monkeypatch):
    """Point HERMES_HOME at a fresh temp dir for every agent test."""
    fake_home = tmp_path / "hermes_home"
    fake_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    yield fake_home
