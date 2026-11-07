import os
import re
import sys

checks = [
    ("check1", r"default=(98|75|18|38|4\.5|16\.2)", "backend/app"),
    ("check2", r"else (22|56)\.0", "backend/app"),
    ("check3", r"get_textbook_ideal_landmarks|textbook_|is_textbook", ["backend", "frontend/src"]),
    ("check4", r"generate_text_async|run_gemini", ["backend", "frontend/src"]),
    ("check5", r"Comparison failed: \{", "backend"),
    ("check6", r"date_of_birth=date\(2000", "backend/app"),
    ("check7", r"benchmark-presets|_get_or_create_benchmark_athlete|Benchmark Reference", ["backend", "frontend/src"]),
    ("check8", r"Olympic|publication-grade|Clinical Impact|Prescribed Neuromuscular|Clinical Biomechanical", ["backend", "frontend/src"]),
    ("check9", r"audioCue|agy_benchmark_active", "frontend/src"),
    ("check10", r"coach_code", ["backend", "frontend/src"]),
]

exclude_dirs = {".git", "node_modules", ".next", "__pycache__", ".hypothesis", ".pytest_cache", "uploads", "data", "test-assets", ".venv", "venv", "real-corpus"}
exclude_files = {"check_acceptance.py", "REPORT.md", "BRIEF.md"}

all_passed = True
for name, pattern, target in checks:
    cp = re.compile(pattern, re.IGNORECASE)
    targets = [target] if isinstance(target, str) else target
    hits = []
    for t in targets:
        for root, dirs, files in os.walk(t):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f in exclude_files or f.endswith((".pyc", ".png", ".jpg", ".task", ".pt")):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for lno, line in enumerate(fh, 1):
                            if cp.search(line):
                                hits.append((path, lno, line.strip()))
                except Exception:
                    pass
    if hits:
        print(f"FAILED {name} ({pattern}): {len(hits)} hits")
        for h in hits[:5]:
            print(f"   {h[0]}:{h[1]}: {h[2]}")
        all_passed = False
    else:
        print(f"PASSED {name}")

print(f"ALL ACCEPTANCE GREPS PASSED: {all_passed}")
if not all_passed:
    sys.exit(1)
