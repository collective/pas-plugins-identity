"""Shared constants for the ``[server]`` extra's tests."""

from pas.plugins.identity import PACKAGE_NAME


#: The GenericSetup profile that installs the extra. Applied per test module
#: through ``@pytest.mark.portal``, so a module that does not ask for it runs
#: against a site where the authorization server was never switched on.
PROFILE_ID = f"{PACKAGE_NAME}:server"

#: The profile that removes it again.
UNINSTALL_PROFILE_ID = f"{PACKAGE_NAME}:uninstall-server"
