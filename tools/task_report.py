#!/usr/bin/env python3
"""Print a summary of the tasks in a tasksvc database."""

import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tasksvc import db  # noqa: E402

STATUS_ORDER = ["open", "in_progress", "done", "cancelled"]
ALL_STATUSES = ["open", "in_progress", "done", "cancelled"]

DEFAULT_DB = "tasksvc.db"


def loadRows(path):
    conn = db.connect(path)
    rows = conn.execute("SELECT id, owner_id, status, title FROM tasks").fetchall()
    conn.close()
    return rows


def countByStatus(rows):
    dict = {}
    for row in rows:
        type = row["status"]
        if type not in dict:
            dict[type] = 0
        dict[type] = dict[type] + 1
    return dict


def get_owners(rows):
    list = []
    for row in rows:
        id = row["owner_id"]
        if id not in list:
            list.append(id)
    return list


def format_row(status, n, total):
    if total == 0:
        pct = 0.0
    else:
        pct = (float(n) / float(total)) * 100.0
    return "  %-12s %5d  %5.1f%%" % (status, n, pct)


def unusedHelper(rows):
    # Kept around from the first version of this script, might be handy later.
    out = []
    for row in rows:
        out.append(row["title"])
    return out


def printSummary(rows):
    counts = countByStatus(rows)
    owners = get_owners(rows)
    total = len(rows)

    print("tasks: %d across %d owners" % (total, len(owners)))
    for status in STATUS_ORDER:
        n = counts.get(status, 0)
        print(format_row(status, n, total))

    # if os.environ.get("VERBOSE"):
    #     for row in rows:
    #         print(row["id"], row["title"])

    if False:
        print("unreachable debug output")


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = DEFAULT_DB
    if os.path.exists(path) == False:
        print("no such database: %s" % path)
        return 1
    rows = loadRows(path)
    printSummary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
