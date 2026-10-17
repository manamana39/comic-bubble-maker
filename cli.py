"""
CLI entry point for Comic Bubble Engine.
Usage:
    python cli.py --config sample_config.json
    python cli.py --image input/sample.jpg --text "こんにちは" --center 0.2,0.2 --output output/out.png
    python cli.py --verify
"""

import sys
import os
import json
import argparse
from comic_bubble import __version__, render_from_file, render_scene, SceneConfig, BubbleConfig
from comic_bubble.fonts import FONT_CANDIDATES, resolve_font_path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Comic Bubble Engine - Japanese Speech Bubble & Floating Monologue Renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", "-c", type=str, help="Path to JSON configuration file")
    parser.add_argument("--image", "-i", type=str, help="Path to input image")
    parser.add_argument("--text", "-t", type=str, help="Text to render in bubble or monologue")
    parser.add_argument("--type", type=str, default="capsule",
                        choices=["capsule", "cloud", "oval", "box", "floating", "monologue"],
                        help="Bubble shape or 'floating'/'monologue' for borderless thoughts")
    parser.add_argument("--center", type=str, help="Center coordinate as 'x,y' (e.g. '0.2,0.25')")
    parser.add_argument("--tail", type=str, help="Tail target coordinate as 'x,y' (e.g. '0.35,0.40')")
    parser.add_argument("--font", type=str, default="kiwi", help="Font alias (kiwi, ud, mincho, etc.)")
    parser.add_argument("--output", "-o", type=str, default="output/result.png", help="Output image file path")
    parser.add_argument("--list-fonts", action="store_true", help="List resolved font paths on this system")
    parser.add_argument("--verify", action="store_true", help="Run automated test suite and exit")
    parser.add_argument("--version", "-v", action="version", version=f"Comic Bubble Engine v{__version__}")
    return parser.parse_args()

def main():
    args = parse_args()

    if args.verify:
        print("[*] Running automated verification suite...")
        import subprocess
        result = subprocess.run([sys.executable, "run_verification.py"])
        sys.exit(result.returncode)

    if args.list_fonts:
        print("=== Registered Font Resolvers ===")
        for alias, paths in FONT_CANDIDATES.items():
            resolved = resolve_font_path(alias)
            status = f"FOUND: {resolved}" if resolved else "NOT FOUND (Will fallback)"
            print(f"  [{alias:8s}] -> {status}")
        sys.exit(0)

    if args.config:
        if not os.path.exists(args.config):
            print(f"[ERROR] Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        out = render_from_file(args.config, args.output if args.output != "output/result.png" else None)
        print(f"[SUCCESS] Saved composite image: {out}")
        sys.exit(0)

    if args.image and args.text:
        center = None
        if args.center:
            parts = [float(p.strip()) for p in args.center.split(",")]
            center = (parts[0], parts[1])

        tail = None
        if args.tail:
            parts = [float(p.strip()) for p in args.tail.split(",")]
            tail = (parts[0], parts[1])

        bubble = BubbleConfig(
            text=args.text.replace("\\n", "\n"),
            type=args.type,
            font=args.font,
            center=center if center else (0.2, 0.2),
            tail=tail
        )
        scene = SceneConfig(
            image_path=args.image,
            bubbles=[bubble],
            output_path=args.output
        )
        result = render_scene(scene)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        result.save(args.output, quality=98)
        print(f"[SUCCESS] Rendered and saved: {args.output}")
        sys.exit(0)

    parser = argparse.ArgumentParser()
    print("Comic Bubble Engine - Please provide --config or --image and --text. Run with --help for options.")
    sys.exit(1)

if __name__ == "__main__":
    main()
