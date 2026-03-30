from pathlib import Path
import sys

from setuptools import setup


PROJECT_ROOT = Path(__file__).resolve().parent

# Avoid local test.py shadowing the stdlib test package during py2app's import scan.
project_root_str = str(PROJECT_ROOT)
sys.path = [entry for entry in sys.path if entry not in ("", project_root_str)] + [project_root_str]

try:
    import py2app.recipes.tkinter as py2app_tkinter_recipe
except Exception:
    py2app_tkinter_recipe = None
else:
    # py2app's default tkinter recipe calls _tkinter.create() during build-time
    # Tk probing, which aborts in this environment. The app itself still imports
    # tkinter at runtime, so skip the recipe-time probe and let macOS system Tcl/Tk
    # resolve normally from the bundled interpreter.
    py2app_tkinter_recipe.check = lambda cmd, mf: None


def resource_entries(relative_dir: str) -> tuple[str, list[str]]:
    base = PROJECT_ROOT / relative_dir
    files = [str(path) for path in sorted(base.rglob("*")) if path.is_file()]
    return relative_dir, files


APP = ["baseline_agent.py"]
DATA_FILES = [
    resource_entries("templates"),
    resource_entries("skills"),
    resource_entries("cases"),
]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["runtime", "skills", "openpyxl"],
    "excludes": ["test"],
    "includes": [
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
        "tkinter.simpledialog",
        "tkinter.ttk",
    ],
    "resources": ["templates", "skills", "cases"],
    "plist": {
        "CFBundleName": "Cloud Security Baseline Agent",
        "CFBundleDisplayName": "Cloud Security Baseline Agent",
        "CFBundleIdentifier": "com.ryan.cloud-security-baseline-agent",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
    },
}


setup(
    app=APP,
    name="Cloud Security Baseline Agent",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
