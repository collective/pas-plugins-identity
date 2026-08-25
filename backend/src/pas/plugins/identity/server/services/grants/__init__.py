"""``@oauth-grants`` -- the applications a user has authorized.

The mirror image of ``@identities``. That endpoint lists the providers
somebody signs in *with* and lets them unlink one; this one lists the
applications they have signed in *to* and lets them withdraw. A person who
can see the first and not the second can see half of what this site knows
about their account.

Deliberately not the admin API. ``@identity-clients`` is the operator's view
of the client registry and needs ``Manage portal``; this is the caller's view
of their own agreements, and needs only that they are the caller. The two
answer about the same clients and are not the same question: an operator asks
"who may log in to this site", a person asks "who did I let in".

Withdrawing does two things, and it takes both to mean anything. Forgetting
the consent record decides what happens the next time that client asks --
they get prompted, as they were the first time. Revoking the client's refresh
tokens for that user is what ends the access they already have. Access tokens
are self-encoded with no denylist, so any already minted live out their
lifetime; the response says how long that can be rather than letting a screen
imply an instant cutoff.
"""
