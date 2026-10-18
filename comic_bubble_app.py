"""
comic_bubble_app.py
~~~~~~~~~~~~~~~~~~~
Desktop entry point for Manga Comic Bubble Maker.
Run directly with python or double-click start_app.bat on Windows.
"""

import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    # Enable high-DPI scaling for sharp rendering on Windows displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Comic Bubble Maker")
    app.setOrganizationName("ComicBubble")

    initial_image = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.isfile(arg):
            initial_image = arg

    window = MainWindow(initial_image=initial_image)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
