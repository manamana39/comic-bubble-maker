from setuptools import setup, find_packages

setup(
    name="comic-bubble-maker",
    version="0.5.0-beta",
    description="Intelligent Japanese Manga Speech Bubble & Floating Monologue Engine",
    author="Antigravity Team",
    packages=find_packages(),
    install_requires=[
        "Pillow>=10.0.0",
        "numpy>=1.20.0",
    ],
    entry_points={
        "console_scripts": [
            "comic-bubble=cli:main",
        ],
    },
    python_requires=">=3.8",
)
