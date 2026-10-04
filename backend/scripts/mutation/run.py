"""Mutation harness: inject ONE bug at a time into a disposable COPY of the backend, run the relevant
tests, and report whether the suite noticed (KILLED) or not (SURVIVED).

    cd backend
    python scripts/mutation/run.py scripts/mutation/mutants.py              # whole catalogue
    python scripts/mutation/run.py scripts/mutation/mutants.py S08 A06      # selected ids
    MUT_OUT=/tmp/results.jsonl python scripts/mutation/run.py scripts/mutation/mutants_followup.py

Requirements: the normal test environment (Postgres on the port conftest.py expects + Redis running).
The real source tree is never modified. Results append to $MUT_OUT (default: ./mutation_results.jsonl) and a
finished id is skipped on re-run, so an interrupted campaign resumes where it stopped.

A mutant is {"id","file","old","new","desc","tests"}: `old` must occur exactly once in `file` (or set
"all": True to replace every occurrence). A SURVIVED mutant means a test gap OR an equivalent mutant
(one that cannot change behaviour) — decide which before dismissing it. Two no-op CONTROL mutants (B02, V11)
must always survive; if one is "killed" the harness itself is wrong.

Mutations of numeric constants assume the values in the catalogue; if the engine's constants change, a
mutant reports BAD_MUTANT ("old string found 0x") — update the catalogue.
"""
import json, os, shutil, subprocess, sys, tempfile, time

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TREE = os.path.join(tempfile.gettempdir(), "mutation_tree")
OUT = os.environ.get("MUT_OUT", "mutation_results.jsonl")


def fresh_tree():
    shutil.rmtree(TREE, ignore_errors=True)
    shutil.copytree(SRC, TREE, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".hypothesis", ".venv", "venv"))


def run_tests(selection, timeout):
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-x", "-q", *selection.split()]
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=TREE, capture_output=True, text=True, timeout=timeout)
        failed = [l for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))]
        return r.returncode, ((r.stdout.strip().splitlines() or [""])[-1]), failed[:1], time.time() - t
    except subprocess.TimeoutExpired:
        return "timeout", "", [], time.time() - t


def main(catalogue, only=None):
    ns = {}
    exec(open(catalogue).read(), ns)
    fresh_tree()
    done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
    for m in ns["MUTANTS"]:
        if m["id"] in done or (only and m["id"] not in only):
            continue
        path = os.path.join(TREE, m["file"])
        orig = open(path).read()
        n = orig.count(m["old"])
        rec = {"id": m["id"], "file": m["file"], "desc": m["desc"]}
        if n == 0 or (n > 1 and not m.get("all")):
            rec.update(status="BAD_MUTANT", detail=f"old string found {n}x")
        else:
            open(path, "w").write(orig.replace(m["old"], m["new"]) if m.get("all") else orig.replace(m["old"], m["new"], 1))
            try:
                rc, tail, failed, secs = run_tests(m["tests"], m.get("timeout", 240))
            finally:
                open(path, "w").write(orig)
            status = "SURVIVED" if rc == 0 else "KILLED" if rc == 1 else f"ERR({rc})"
            rec.update(status=status, secs=round(secs, 1), killed_by=(failed[0][:110] if failed else tail[:110]))
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(rec["id"], rec["status"], rec.get("killed_by", ""), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]) or None)
