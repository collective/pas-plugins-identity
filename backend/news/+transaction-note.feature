A login now says so in the transaction it commits.

Zope writes a transaction's description in `ZPublisher.utils.recordMetaData`, which runs after traversal and *before* the view is called. On a federated login the view is where authentication happens, so the one transaction that mints an account, writes several hundred objects and joins a person to a userid was committing as a bare `/plone/@identity-callback` attributed to nobody. The undo log could not say who signed in, or that a login was what it had been looking at.

`core/txn.py` adds a line per fact, and `Transaction.note` appends rather than replaces, so Zope's path stays where it was:

```text
/plone/@identity-callback
identity: login 8f2c1e... via github (new user, new identity)
identity: profile created at /plone/users/8f2c1e...
```

A login against a local password is recorded the same way, naming the login offered. The transaction is also attributed to the userid, which Zope could not do because at traversal time the person was still anonymous — unless it already names somebody, so a request genuinely made by an administrator keeps its own attribution.

No claims, no address, no provider subject. A transaction record is never purged short of packing the storage, which makes it the worst available home for personal data; the userid is opaque and a provider id is site configuration. Nothing here joins the transaction either, so a request that wrote nothing goes on writing nothing. @ericof
