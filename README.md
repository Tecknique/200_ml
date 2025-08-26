#README.md


# Portable Voilà App (Windows)

**How to run**
1. Download ZIP of this repo, extract it.
2. Double-click `run_app_portable.bat`.
   - First run installs Miniforge and builds a local env in `./env`.
   - Browser opens at: http://127.0.0.1:8866/voila/render/app.ipynb

**Files**
- `one_cell_app.py` — app code
- `app.ipynb` — thin wrapper notebook
- `environment.yml` — env spec (conda-forge)
- `run_app_portable.bat` — portable launcher (no preinstalled Python needed)

**Notes**
- Works on Windows 10/11 x64 (ARM64: swap installer URL inside the BAT).
- Do **not** commit `env/` or `bin/` — they’re recreated automatically.
