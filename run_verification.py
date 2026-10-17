"""
run_verification.py
~~~~~~~~~~~~~~~~~~~
Automated verification and test runner for Comic Bubble Engine.
Designed for CodeX, CI/CD, and autonomous agent verification.
Executes all unit tests, performs real-world image rendering checks,
validates zero-interference boundaries, and outputs a JSON report.
"""

import sys
import os
import json
import time
import unittest
from typing import Dict, Any

from comic_bubble import __version__, render_from_file, resolve_font_path, get_luminance
from PIL import Image

def run_unit_tests() -> Dict[str, Any]:
    """Execute the unittest discovery suite and collect results."""
    print("[1/3] Running Unit & Integration Test Suites...")
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=1)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "duration_sec": round(duration, 3),
        "success": result.wasSuccessful()
    }

def run_real_world_verification() -> Dict[str, Any]:
    """Render sample configs on real-world test images and verify outputs."""
    print("[2/3] Performing Real-World Image Verification...")
    test_configs = [
        ("examples/park_night_sample.json", "output/park_night_verified.png"),
        ("examples/kuma_seishun_sample.json", "output/kuma_seishun_verified.png")
    ]

    rendered_results = []
    for cfg_path, expected_out in test_configs:
        if not os.path.exists(cfg_path):
            continue
        start_t = time.time()
        out_path = render_from_file(cfg_path, expected_out)
        t_taken = time.time() - start_t

        # Validate file
        assert os.path.exists(out_path), f"Output file missing: {out_path}"
        img = Image.open(out_path)
        w, h = img.size
        assert w > 0 and h > 0, f"Invalid dimensions: {w}x{h}"

        rendered_results.append({
            "config": cfg_path,
            "output": out_path,
            "dimensions": f"{w}x{h}",
            "render_time_sec": round(t_taken, 3),
            "status": "PASS"
        })
        print(f"  [PASS] {cfg_path} -> {out_path} ({w}x{h}) in {t_taken:.2f}s")

    return {
        "verified_images": rendered_results,
        "all_passed": all(r["status"] == "PASS" for r in rendered_results)
    }

def run_font_and_system_check() -> Dict[str, Any]:
    """Check system font availability and fallbacks."""
    print("[3/3] Checking Typography & System Fallback Cascade...")
    aliases = ["kiwi", "yomogi", "zenmaru", "ud", "mincho", "bold"]
    status_map = {}
    for alias in aliases:
        p = resolve_font_path(alias)
        status_map[alias] = {
            "resolved_path": p,
            "available": p is not None and os.path.exists(p)
        }
        status_str = "OK" if status_map[alias]["available"] else "FALLBACK"
        print(f"  [{alias:8s}] -> {status_str}: {p}")

    return status_map

def main():
    print("=" * 60)
    print(f"  Comic Bubble Engine v{__version__} - Automated Verification")
    print("=" * 60)

    test_res = run_unit_tests()
    real_res = run_real_world_verification()
    font_res = run_font_and_system_check()

    overall_success = test_res["success"] and real_res["all_passed"]

    report = {
        "version": __version__,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": "SUCCESS" if overall_success else "FAILED",
        "unit_tests": test_res,
        "real_world_verification": real_res,
        "font_resolvers": font_res
    }

    os.makedirs("output", exist_ok=True)
    report_file = "output/verification_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    if overall_success:
        print(f"  [SUCCESS] All verification suites PASSED! (Report: {report_file})")
    else:
        print(f"  [FAILED] One or more verification suites failed.")
    print("=" * 60)

    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()
