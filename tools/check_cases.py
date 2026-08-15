#!/usr/bin/env python3
"""Validate evals/cases.yaml against the live pull-request diffs.

Checks, for every case:

* the file parses and carries the required fields;
* ``expected_route`` and every ``min_severity`` use a known value;
* every ``file`` path is repo-relative (no ``a/`` or ``b/`` prefix);
* every ``near_line`` points at a line the pull request actually touched, using
  new-version line numbers taken from the unified diff;
* conflict cases name two different reviewers and land inside LINE_PROXIMITY.

Requires ``gh`` (authenticated) and PyYAML. Run it after editing the manifest or
force-pushing a fixture branch:

    python3 tools/check_cases.py
"""

import os
import re
import subprocess
import sys

import yaml

ROUTES = {"arbitrate", "human_approval", "loop_then_approve", "ceiling"}
SEVERITIES = ["none", "nit", "minor", "major", "blocker"]
REVIEWERS = {"correctness", "style", "security"}
CONFLICT_KINDS = {"opposed_recommendations", "severity_gap"}
LINE_PROXIMITY = 5

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "evals", "cases.yaml")


def touched_lines(pr_number):
    """Map file -> set of new-version line numbers added by this pull request."""
    diff = subprocess.run(
        ["gh", "pr", "diff", str(pr_number)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    touched, current, line_no = {}, None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current = raw[6:]
            touched.setdefault(current, set())
        elif raw.startswith("@@"):
            line_no = int(re.search(r"\+(\d+)", raw).group(1))
        elif current and raw.startswith("+") and not raw.startswith("+++"):
            touched[current].add(line_no)
            line_no += 1
        elif current and (raw.startswith(" ") or raw == ""):
            line_no += 1
    return touched


def main():
    with open(MANIFEST, encoding="utf-8") as handle:
        cases = yaml.safe_load(handle)

    problems = []
    seen_ids = set()

    for case in cases:
        cid = case.get("id", "<missing id>")
        if cid in seen_ids:
            problems.append(f"{cid}: duplicate id")
        seen_ids.add(cid)

        for required in ("id", "pr_ref", "intent", "expected_route", "notes"):
            if not case.get(required):
                problems.append(f"{cid}: missing required field {required!r}")
        if "must_flag" not in case:
            problems.append(f"{cid}: missing required field 'must_flag'")

        route = case.get("expected_route")
        if route not in ROUTES:
            problems.append(f"{cid}: unknown expected_route {route!r}")
        if route == "arbitrate" and "expected_conflict" not in case:
            problems.append(f"{cid}: routes to arbitrate but has no expected_conflict")

        match = re.match(r"^[\w.-]+/[\w.-]+#(\d+)$", case.get("pr_ref", ""))
        if not match:
            problems.append(f"{cid}: pr_ref must look like owner/repo#123")
            continue
        pr_number = int(match.group(1))

        try:
            touched = touched_lines(pr_number)
        except subprocess.CalledProcessError as exc:
            problems.append(f"{cid}: could not read diff for PR #{pr_number}: {exc}")
            continue

        anchors = list(case.get("must_flag") or [])
        conflict = case.get("expected_conflict")
        if conflict:
            reviewers = conflict.get("reviewers") or []
            if len(set(reviewers)) != 2 or not set(reviewers) <= REVIEWERS:
                problems.append(f"{cid}: expected_conflict needs two distinct reviewers")
            if conflict.get("kind") not in CONFLICT_KINDS:
                problems.append(f"{cid}: unknown conflict kind {conflict.get('kind')!r}")
            anchors.append(conflict)

        for anchor in anchors:
            path = anchor.get("file", "")
            if path.startswith(("a/", "b/")):
                problems.append(f"{cid}: {path!r} has a diff prefix; use a repo-relative path")
            severity = anchor.get("min_severity")
            if severity is not None and severity not in SEVERITIES:
                problems.append(f"{cid}: unknown min_severity {severity!r}")

            if path not in touched:
                problems.append(f"{cid}: PR #{pr_number} does not touch {path}")
                continue

            line = anchor.get("near_line")
            if line is None:
                continue
            if line not in touched[path]:
                near = sorted(touched[path])
                closest = min(near, key=lambda n: abs(n - line)) if near else None
                problems.append(
                    f"{cid}: {path}:{line} is not a line PR #{pr_number} added"
                    + (f" (closest added line is {closest})" if closest else "")
                )

        if conflict and case.get("must_flag"):
            same_file = [
                f["near_line"]
                for f in case["must_flag"]
                if f.get("file") == conflict.get("file") and f.get("near_line")
            ]
            for line in same_file:
                if abs(line - conflict["near_line"]) > LINE_PROXIMITY:
                    problems.append(
                        f"{cid}: must_flag line {line} is more than {LINE_PROXIMITY}"
                        f" lines from the conflict anchor {conflict['near_line']}"
                    )

    print(f"checked {len(cases)} cases")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("all anchors resolve to lines their pull request actually added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
