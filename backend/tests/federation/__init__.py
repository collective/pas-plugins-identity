"""This package federating with itself.

:mod:`tests.federation.test_handlers` runs in process against the integration
site and covers what the demo *handlers* do — the client, the provider, the
user, the guard — and that the constants they read agree with the profile XML
GenericSetup reads.

The Docker half, a real relying party completing a real login against a real
authorization server in two separate Plone sites, is not here yet: standing
the stack up by hand got as far as the authorization code reaching the relying
party and then failed at the token endpoint, on a mismatch between the client
authentication authlib sends and the one the server accepts. That is a defect
in the package rather than in the demo, so the test that would assert the flow
is waiting on the fix.
"""

from pas.plugins.identity import PACKAGE_NAME


#: The ``[server]`` profile, which the identity-provider side needs before
#: there is a client registry to register anything in.
SERVER_PROFILE_ID = f"{PACKAGE_NAME}:server"
