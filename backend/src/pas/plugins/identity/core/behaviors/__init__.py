"""The behaviors a site can turn on for its user and group types.

One module per behavior, because that is what a behavior is: a schema, a
factory where it needs one, and the registration that offers it. Nothing is
re-exported here -- a consumer names the behavior it means.

:mod:`~pas.plugins.identity.core.behaviors.password.password` is opt-in and stores a
credential; :mod:`~pas.plugins.identity.core.behaviors.password.membership` is
schema-only and is enabled on both shipped types. Their ZCML lives beside
them in ``configure.zcml``.
"""
