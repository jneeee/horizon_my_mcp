"""Pytest config: ensure TAVILY_API_KEY is set so module-level imports
that lazily touch it do not blow up. Tests that need to assert the
'missing key' path explicitly delete it via monkeypatch.
"""
import os

os.environ.setdefault("TAVILY_API_KEY", "test-key-not-used")
