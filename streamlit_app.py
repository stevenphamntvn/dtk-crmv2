"""The same entry point is used on Windows and Streamlit Cloud."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
for folder in (ROOT, ROOT / "Data"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
runpy.run_path(str(ROOT / "Data" / "crm_app.py"), run_name="__main__")
