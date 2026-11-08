"""Compatibility entry point for the standalone file engine regression suite."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[2]/"tools/test_n67_files.py"),run_name="__main__")
