"""Supervisor middleware — policy gates run in fixed order.

Order matters:
    1. ethics   — reject taskings that are out of mission even if scoped
    2. scope    — allow-list match, time window, restriction match
    3. budget   — per-tasking ceiling
    4. rate     — per-source rate limits
    5. audit    — fire-and-forget write of every transition

Every gate returns a list of `Violation` records. An empty list means "pass".
The supervisor refuses to advance while any prior step produced violations.
"""

from agents.supervisor.middleware.audit import write_audit
from agents.supervisor.middleware.budget import check_budget
from agents.supervisor.middleware.ethics import check_ethics
from agents.supervisor.middleware.rate_limit import check_rate_limit
from agents.supervisor.middleware.scope import check_scope

__all__ = [
    "check_budget",
    "check_ethics",
    "check_rate_limit",
    "check_scope",
    "write_audit",
]
