"""Shared constants for the ``[server]`` extra's tests."""

from pas.plugins.identity import PACKAGE_NAME


#: The GenericSetup profile that installs the extra. Applied per test module
#: through ``@pytest.mark.portal``, so a module that does not ask for it runs
#: against a site where the authorization server was never switched on.
PROFILE_ID = f"{PACKAGE_NAME}.server:default"

#: The profile that removes it again.
UNINSTALL_PROFILE_ID = f"{PACKAGE_NAME}.server:uninstall"

#: The issuer this site publishes itself under. Nothing is signed until it is
#: configured, so most modules here set it in a fixture before anything else.
ISSUER = "https://id.example.org"

#: A registered client's redirect URI. A different origin from the issuer on
#: purpose: a relying party is somebody else's deployment, and a test that
#: redirected back to the issuer would not notice a URI built from the wrong
#: one.
REDIRECT = "https://app.example.org/cb"

#: The person tokens are minted for. A module that needs to tell two users
#: apart names the second one itself rather than adding a constant here.
USERID = "alice"

#: The account a ``client_credentials`` client acts as. Named like a service
#: rather than a person because that is what the grant is for: no human is
#: present at the far end of it, and a token that says ``alice`` would put one
#: in the audit log.
SERVICE_USER = "svc-indexer"
