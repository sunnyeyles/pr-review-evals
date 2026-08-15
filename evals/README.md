# The eval manifest

`cases.yaml` is the deliverable of this repository. The pull requests are its
raw material: each one has a deliberately planted, known answer, and the
manifest records what that answer is so a scoring harness can grade a reviewer's
output automatically instead of a human eyeballing it.

**Everything in this repository is a fixture.** The pull requests introduce real
security holes and real bugs on purpose. Do not copy code out of them.

## The reviewer these cases are written against

`review-pr` is a LangGraph pipeline:

```
fetch_pr → {review_correctness, review_style, review_security}  (parallel)
         → synthesize → router → arbitrate | loop back | human_approval
```

Three reviewers look at the same diff through different lenses and emit
`Verdict` objects; a deterministic router then picks the next edge. The cases
here exist to drive that router down every branch, so they are designed against
its predicates rather than against any particular model's taste.

A `Verdict` carries `reviewer`, `file`, `line` (or `null` for a file-level
finding), `severity` (`none` < `nit` < `minor` < `major` < `blocker`),
`recommendation` (`approve` / `comment` / `request_changes`) and `confidence`.

**A conflict** routes to `arbitrate`. It needs two verdicts that are from
different reviewers, in the same file with lines within `LINE_PROXIMITY` (5) of
each other, both at confidence `≥ CONFIDENCE_FLOOR` (0.6), and either opposed
recommendations (`approve` vs `request_changes`) or a severity gap of at least
two ranks.

**A thin pass** loops back to all three reviewers. It is any of: zero verdicts,
any one reviewer emitting nothing at all, fewer than `MIN_VERDICTS` (3) verdicts
in total, or mean confidence below the floor. Looping is bounded by
`MAX_REVIEW_PASSES` (3).

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable kebab-case identifier. Scoring output is keyed on it, so do not rename one after results exist. |
| `pr_ref` | yes | `owner/repo#number`. The pull request stays **open** forever; merging it would change the diff and invalidate the expectations below. |
| `intent` | yes | What was planted and why, in prose. This is the human-readable answer key. |
| `expected_route` | yes | One of `arbitrate`, `human_approval`, `loop_then_approve`, `ceiling`. See below. |
| `expected_conflict` | conflict cases | The specific pair of lenses expected to collide, and where. |
| `must_flag` | yes | Findings the reviewer has to produce. An **empty list is meaningful**: it asserts the correct answer is "nothing to flag". |
| `must_not_flag` | traps | Findings that must not be the top result. Flagging one is not automatically a failure — leading with it is. |
| `notes` | yes | What this case is actually testing, and anything a future maintainer needs in order to not break it. |

### `expected_route`

| Value | Meaning |
| --- | --- |
| `human_approval` | Reviewers produced enough confident, non-contradictory verdicts on the first pass. |
| `arbitrate` | The conflict predicate fired. Only for cases that also carry `expected_conflict`. |
| `loop_then_approve` | The first pass was thin, the graph looped, and a later pass settled at `human_approval`. |
| `ceiling` | The pass stays thin no matter how many times it runs; the graph must terminate at `MAX_REVIEW_PASSES` rather than spin. |

### `must_flag` entries

```yaml
must_flag:
  - file: "src/tasksvc/auth.py"   # repo-relative, no a/ or b/ prefix
    near_line: 43                 # NEW-VERSION line number, as in the unified diff
    issue: "what is wrong, in one sentence"
    min_severity: major           # none | nit | minor | major | blocker
```

`file` and `near_line` are the two fields that silently break scoring when they
are wrong. The reviewer matches `file` by exact string equality, so a stray
`b/` prefix scores as a miss on a finding that was actually made. `near_line`
must be the line number **in the new version of the file**, which is the number
`git show <branch>:<path>` produces, not the position within the hunk. A verdict
with `line: null` covers the whole file and matches any `near_line` in it.

## Adding a case

1. Branch off `main` and plant the flaw. Keep it to **1–3 changed files** —
   the whole diff goes into three model prompts on every pass.
2. Give the branch a title and body a real contributor would write. **Do not
   describe the planted flaw in the pull request body**: that leaks the answer
   straight into the reviewer's context and the case stops measuring anything.
3. Confirm the flaw is real by running it, not by reading it. Every correctness
   claim in `cases.yaml` was reproduced against its branch before it was
   written down.
4. Open the pull request and **leave it open**.
5. Read the unified diff and take the new-version line numbers from it. To
   check an anchor:

   ```bash
   git show <branch>:<path> | sed -n '<line>p'
   ```

6. Add the entry to `cases.yaml` and re-run the validator below.

Do not add CI, linters or pre-commit hooks to this repository. An automated
formatter that "fixes" a planted flaw destroys the fixture it lives in — the
whitespace-only case in particular cannot survive a formatter.

## Validating the manifest

`tools/check_cases.py` re-derives every anchor from the live pull-request diffs
and fails if any `file`/`near_line` pair no longer points at a line that pull
request actually touched:

```bash
python3 tools/check_cases.py      # needs gh, authenticated, and PyYAML
```

Run it after editing `cases.yaml`, and after any force-push to a fixture branch.

## Designing a conflict

Conflicts have to be real, not produced by prompt-stuffing. The reliable recipe
is code where the lenses genuinely see different things **at the same lines**:

- A cache that is correct and fast but caches an authorisation decision —
  correctness approves, security blocks. (`conflict-principal-cache`)
- A swallowed exception: style calls it a nit, security calls it a lost audit
  trail. (`conflict-swallowed-audit-write`)
- Validation that is thorough but rejects valid unicode — security approves,
  correctness calls it a bug.

Keep the conflicting concerns within five lines of each other. Spread them
further and `_same_place` returns false, the conflict never fires, and the case
quietly tests nothing.
