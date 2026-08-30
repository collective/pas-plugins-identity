"""Tests for the two content types this package ships.

``UserProfile`` and ``UserGroup`` are what makes this add-on unusual: a user
and a group are content objects rather than rows in ``source_users``, which is
what lets a Profile carry fields, hold a workflow state and keep a history.

The modules here test the *types* -- the FTI, the behaviours it declares, and
whether versioning is genuinely switched on. What each type does once it
exists is tested next to the code that does it, under ``tests/core``.
"""
