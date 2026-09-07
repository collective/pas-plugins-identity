"""The behaviors a site can turn on for its user and group types.

One module per behavior, because that is what a behavior is: a schema, a
factory where it needs one, and the registration that offers it. Nothing is
re-exported here -- a consumer names the behavior it means.

:mod:`~pas.plugins.identity.core.behaviors.password` is opt-in and stores a
credential. The rest are schema-only, so their fields live on the content
object exactly as declared fields did:
:mod:`~pas.plugins.identity.core.behaviors.membership` is enabled on both
shipped types, while :mod:`~pas.plugins.identity.core.behaviors.email` and
:mod:`~pas.plugins.identity.core.behaviors.details` carry the parts of a
Profile a person fills in. Their ZCML lives beside them in
``configure.zcml``.
"""
