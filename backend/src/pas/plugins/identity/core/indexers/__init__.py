"""Keeping the Profile catalog honest.

Subscribers and indexers, and between them they are the whole reason the churn
test can assert ``catalog count == Profile count`` after any sequence of
operations. One module per concern, and nothing is re-exported here -- a
consumer names the module it means:

* :mod:`~pas.plugins.identity.core.indexers.subscribers` files a Profile in the
  identity catalog as it is added, moved, modified and removed;
* :mod:`~pas.plugins.identity.core.indexers.profile` holds the indexers that
  fold or compute what a Profile field literally holds, for this package's
  catalog only;
* :mod:`~pas.plugins.identity.core.indexers.searchable_text` holds the two
  answers to ``SearchableText``, one per catalog asking.

Their registrations live beside them in ``configure.zcml``.
"""
