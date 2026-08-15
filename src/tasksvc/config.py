"""Runtime configuration for tasksvc.

Every value can be overridden through the environment so that the service can be
run from a container without a config file.
"""

import os

DB_PATH = os.environ.get("TASKSVC_DB", "tasksvc.db")
AUDIT_LOG_PATH = os.environ.get("TASKSVC_AUDIT_LOG", "audit.log")

LISTEN_HOST = os.environ.get("TASKSVC_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("TASKSVC_PORT", "8080"))

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# Roles that are allowed to act on tasks they do not own.
ADMIN_ROLES = frozenset({"admin", "auditor"})
