"""Run the current pinned-source validator; older validators remain alongside their snapshots."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent / "main-98983fa2" / "validate-reference-map.py"), run_name="__main__")
