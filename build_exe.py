"""
build_exe.py
~~~~~~~~~~~~
Packages Comic Bubble Maker into a standalone Windows executable (.exe)
using PyInstaller.
"""

import os
import subprocess
import sys

def build():
    print("Building Comic Bubble Maker Windows Standalone Executable...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ComicBubbleMaker",
        "--windowed",  # No console window
        "--noconfirm",
        "--clean",
        "--add-data=fonts;fonts",
        "--hidden-import=PySide6",
        "--hidden-import=PIL",
        "--hidden-import=numpy",
        "--hidden-import=requests",
        "--hidden-import=google.genai",
        "comic_bubble_app.py"
    ]
    print("Running command:", " ".join(cmd))
    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        print("\n[SUCCESS] Build completed! Executable is at: dist/ComicBubbleMaker/ComicBubbleMaker.exe")
    else:
        print("\n[FAILED] Build failed with return code:", ret.returncode)

if __name__ == "__main__":
    build()
