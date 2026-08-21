"""Fixtures for the event-contract tests.

The event-discipline tests drive the real services, so they need the same
request, provider and stubbed-network fixtures the service tests use. They
are re-exported rather than duplicated: two copies of a provider stub drift,
and then one suite is testing something the other is not.
"""

from ..services.conftest import configured  # noqa: F401
from ..services.conftest import log  # noqa: F401
from ..services.conftest import request_  # noqa: F401
from ..services.conftest import stub_metadata  # noqa: F401
from ..services.conftest import stub_provider  # noqa: F401
