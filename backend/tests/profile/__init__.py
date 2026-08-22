"""Shared constants for the ``[profile]`` extra's tests."""

from pas.plugins.identity import PACKAGE_NAME


#: The GenericSetup profile that installs the extra. Applied per test module
#: through ``@pytest.mark.portal``, so a module that does not ask for it runs
#: against a site where the extra was never installed.
PROFILE_ID = f"{PACKAGE_NAME}:profile"
