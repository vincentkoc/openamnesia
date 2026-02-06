"""Package-wide constants and defaults."""

from __future__ import annotations

APP_NAME = "openamnesia"

ENV_LOG_LEVEL = "AMNESIA_LOG_LEVEL"

DEFAULT_LOG_LEVEL = "INFO"

STATUS_IDLE = "idle"
STATUS_INGESTING = "ingesting"
STATUS_ERROR = "error"
STATUS_NEVER_RUN = "never-run"

# When True, iMessage permission failures auto-open macOS Full Disk Access settings.
AUTO_REQUEST_DISK_ACCESS_ON_PERMISSION_ERROR = True
