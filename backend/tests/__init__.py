"""Test suite for pas.plugins.identity."""

import transaction


def close_the_site(portal) -> None:
    """Take ``View`` away from ``Anonymous`` at the portal root, and commit.

    What a closed intranet looks like, and the only configuration in which an
    endpoint meant for anonymous callers shows which permission it was
    declared with: while ``Anonymous`` holds ``View``, ``zope2.View`` and
    ``zope.Public`` behave identically.

    Committed, because every caller goes through a real publisher, which reads
    the site from the database rather than from this transaction.

    :param portal: The Plone site.
    """
    portal.manage_permission("View", roles=["Manager"], acquire=0)
    transaction.commit()
