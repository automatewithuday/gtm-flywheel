"""Offline tests: no network, no spend. Run with `python -m pytest tests/` from skills/email-waterfall/."""
import subprocess, sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _selftest(module):
    r = subprocess.run([sys.executable, "-m", f"outbound.{module}", "--selftest"], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().endswith("OK"), r.stdout


def test_common_selftest():
    _selftest("common")


def test_waterfall_selftest():
    _selftest("waterfall")
