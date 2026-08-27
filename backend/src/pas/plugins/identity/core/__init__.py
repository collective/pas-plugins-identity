"""Core layer: always installed, never imports from ``profile`` or ``server``.

The public surface of this package is re-exported here so that the optional
layers -- and third-party integrators -- have a single, stable import path.
See the import-linter contract in ``pyproject.toml``.
"""

from pas.plugins.identity.core.events import EmailVerified
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.events import SessionsRevoked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IDriver
from pas.plugins.identity.core.interfaces import IIdentityStore
from pas.plugins.identity.core.patches import apply_patches
from pas.plugins.identity.core.store import IdentityRecord


# PlonePAS's group tool cannot survive a group that only one of its
# managers knows about, and this package is the second manager. Applied
# here because this module is imported by the ZCML that loads the layer.
apply_patches()

__all__ = [
    "EmailVerified",
    "ExternalIdentityAuthenticated",
    "IAuditSink",
    "IDriver",
    "IIdentityStore",
    "IdentityLinked",
    "IdentityRecord",
    "IdentityUnlinked",
    "SessionsRevoked",
    "UserClaimsRefreshed",
]
