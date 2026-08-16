# pr-review-evals

**This repository contains intentionally defective code that exists only as test
fixtures for an automated pull-request reviewer. Do not copy anything from it
into real software.** Several of the open pull requests deliberately introduce
security holes, logic bugs, and bad practice so that a reviewer's output can be
scored against a known correct answer. Nothing here is production code, none of
the credentials in it are real, and none of it targets a real system.

## What is in here

| Path | Purpose |
| --- | --- |
| `src/tasksvc/` | A small, coherent task-tracking service. This is the *clean* baseline that the fixture pull requests are diffed against. |
| `tests/` | Smoke tests for the baseline. |
| `evals/cases.yaml` | The manifest: one entry per fixture pull request, with its expected review outcome. |
| `evals/README.md` | How to read and extend the manifest. |

The pull requests are the fixtures. They are all left **open** on purpose — a
merged branch would change the diff and invalidate every recorded expectation.

## tasksvc

`tasksvc` is a single-process JSON service for tracking tasks, written against
the standard library so it can be read end to end in a few minutes.

```
src/tasksvc/
  api.py       routing and request handlers
  auth.py      bearer-token authentication and per-task authorisation
  audit.py     append-only audit trail for privileged actions
  db.py        SQLite persistence, all queries parameterised
  models.py    User / Task / Page dataclasses
  server.py    http.server adapter
  utils.py     JSON and query-string helpers
```

### Running it

```bash
python -m tasksvc.server        # from inside src/
python -m unittest discover -s tests
```

Configuration comes from the environment: `TASKSVC_DB`, `TASKSVC_HOST`,
`TASKSVC_PORT`, `TASKSVC_AUDIT_LOG`.

### Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/healthz` | Liveness probe, no authentication. |
| `GET` | `/tasks` | Lists the caller's tasks. `?scope=all` is admin-only. |
| `POST` | `/tasks` | Creates a task. |
| `GET` | `/tasks/{id}` | Reads one task. |
| `POST` | `/tasks/{id}/status` | Moves a task between statuses. |

Every request must receive an `Authorization: Bearer <token>` header except the
liveness probe. Tokens are stored as SHA-256 digests, never in plain text.

## Licence

Public domain (CC0). It is fixture data; there is nothing here worth licensing.
