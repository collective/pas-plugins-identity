"""Test suite for pas.plugins.identity."""

import transaction


#: The smallest valid PNG, so a test never carries a binary fixture file. A
#: real image rather than arbitrary bytes, because ``image_scales`` has to be
#: able to scale it.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


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
