#!/usr/bin/env python3
"""
Submit an entry to GitHub-hosted directory lists: fork -> branch -> edit -> PR.

Reads a JSON config describing each target repo, the file to touch, and where in
that file your row belongs. Every edit is anchored to an existing line, so your
entry lands inside the right section (and the right alphabetical slot) instead of
being appended to whatever table happened to come last.

    python3 submit_to_lists.py --config targets.json --dry   # print diffs, change nothing
    python3 submit_to_lists.py --config targets.json         # fork, commit, open PRs
    python3 submit_to_lists.py --config targets.json owner/repo  # just one target

Requires the `gh` CLI, authenticated with repo scope: https://cli.github.com

MIT licensed. Part of https://github.com/n1-ghosty/saascity-launch-kit
"""
import argparse
import base64
import json
import subprocess
import sys
import time

BRANCH = "add-listing"


# --------------------------------------------------------------------------- gh

def gh(args, check=True, stdin=None):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, input=stdin)
    if check and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:4])}: {r.stderr.strip()[:400]}")
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def api(args, check=True, stdin=None):
    return gh(["api"] + args, check=check, stdin=stdin)


# ------------------------------------------------------------------------ edits

def apply_edit(text, edit):
    """Insert edit['content'] into text according to edit['mode']."""
    mode = edit.get("mode", "after")
    content = edit["content"]

    if mode == "append_table":
        lines = text.split("\n")
        i = max(i for i, l in enumerate(lines) if l.startswith("|"))
        lines.insert(i + 1, content)
        return "\n".join(lines)

    if mode == "append_json_array":
        # keep the diff to the added object; do not reformat the whole file
        end = text.rindex("]")
        close = text.rindex("}", 0, end)
        return text[:close + 1] + ",\n" + content + text[close + 1:]

    if mode == "between":
        # first `until` occurring after `anchor` — for nested arrays/objects
        start = text.index(edit["anchor"])
        stop = text.index(edit["until"], start)
        return text[:stop] + content + text[stop:]

    anchor = edit["anchor"]
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if anchor in l]
    if not hits:
        raise RuntimeError(f"anchor not found: {anchor!r}")
    if len(hits) > 1:
        print(f"    note: anchor matched {len(hits)}x, using the first")
    i = hits[0]
    lines.insert(i + 1 if mode == "after" else i, content)
    return "\n".join(lines)


def preview(old, new, path):
    o, n = old.split("\n"), new.split("\n")
    i = next((k for k in range(len(n)) if k >= len(o) or n[k] != o[k]), 0)
    added = len(n) - len(o)
    print(f"  {path}: +{added} line(s) at {i + 1}")
    for line in n[max(0, i - 1):i + max(added, 1) + 1]:
        print("     ", line[:130])


# ------------------------------------------------------------------------- flow

def submit(target, marker, dry=False):
    repo = target["repo"]
    print(f"\n=== {repo}")

    if dry:
        for edit in target["edits"]:
            raw = api([f"repos/{repo}/contents/{edit['path']}", "--jq", ".content"])[0]
            text = base64.b64decode(raw).decode()
            new = apply_edit(text, edit)
            if edit["path"].endswith(".json"):
                json.loads(new)
                print("      json: valid")
            preview(text, new, edit["path"])
        return "dry-run"

    fork = json.loads(api(["-X", "POST", f"repos/{repo}/forks"])[0])["full_name"]
    time.sleep(4)  # a fresh fork is not immediately readable
    default = json.loads(api([f"repos/{repo}"])[0])["default_branch"]
    gh(["repo", "sync", fork, "--source", repo], check=False)

    sha = json.loads(api([f"repos/{fork}/git/ref/heads/{default}"])[0])["object"]["sha"]
    _, err, rc = api(["-X", "POST", f"repos/{fork}/git/refs",
                      "-f", f"ref=refs/heads/{BRANCH}", "-f", f"sha={sha}"], check=False)
    if rc != 0 and "already exists" not in err:
        raise RuntimeError(err)
    if rc != 0:  # branch left over from a previous run — reset it onto the fresh base
        api(["-X", "PATCH", f"repos/{fork}/git/refs/heads/{BRANCH}",
             "-f", f"sha={sha}", "-F", "force=true"])

    for edit in target["edits"]:
        meta = json.loads(api([f"repos/{fork}/contents/{edit['path']}?ref={BRANCH}"])[0])
        text = base64.b64decode(meta["content"]).decode()
        if marker and marker.lower() in text.lower():
            print(f"  {edit['path']}: already listed, skipped")
            continue
        new = apply_edit(text, edit)
        if edit["path"].endswith(".json"):
            json.loads(new)
        api(["-X", "PUT", f"repos/{fork}/contents/{edit['path']}", "--input", "-"],
            stdin=json.dumps({
                "message": target.get("commit", "Add listing"),
                "content": base64.b64encode(new.encode()).decode(),
                "sha": meta["sha"],
                "branch": BRANCH,
            }))
        print(f"  committed {edit['path']}")

    out, err, rc = gh(["pr", "create", "--repo", repo, "--base", default,
                       "--head", f"{fork.split('/')[0]}:{BRANCH}",
                       "--title", target.get("title", "Add listing"),
                       "--body", target.get("body", "")], check=False)
    if rc != 0:
        raise RuntimeError(err[:300])
    print(f"  PR: {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", help="only these owner/repo targets")
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--dry", action="store_true", help="print diffs, change nothing")
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    marker = cfg.get("skipIfPresent", "")
    results = {}
    for target in cfg["targets"]:
        if args.repos and target["repo"] not in args.repos:
            continue
        try:
            results[target["repo"]] = submit(target, marker, args.dry)
        except Exception as e:
            results[target["repo"]] = f"FAILED: {e}"
            print(f"  FAILED: {e}")

    print("\n===== summary =====")
    for repo, result in results.items():
        print(f"{repo}\t{result}")
    return 1 if any(str(v).startswith("FAILED") for v in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
