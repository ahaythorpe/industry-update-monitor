"""Flags that would be silently ignored are refused instead (IMPROVEMENTS.md item 19)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(*flags):
    return subprocess.run([sys.executable, "src/monitor.py", *flags], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)


def test_json_with_brief_or_sweep_is_refused_not_ignored():
    for flags in (["--json", "--brief"], ["--json", "--sweep", "--brief"], ["--json", "--ollama"]):
        result = _run(*flags)
        assert result.returncode != 0, flags
        assert "never fetch" in result.stderr and "--json first" in result.stderr
