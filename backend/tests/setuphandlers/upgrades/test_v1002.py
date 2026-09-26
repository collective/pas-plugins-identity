"""Version 1002: the Profile's fields move onto behaviors.

The FTI half, which ``typeinfo`` carries. An FTI is a persistent object
written at install, so a site installed before this keeps the old behaviors
list: the email tab would not exist and the fields that moved would be missing
from the form rather than relocated.
"""

from plone import api


class TestTheFieldsAreOnBehaviors:
    def test_the_upgrade_restores_them_on_a_site_that_lacks_them(
        self, portal, upgrade_from
    ):
        types = api.portal.get_tool("portal_types")
        types["UserProfile"].behaviors = ("plone.shortname", "plone.versioning")

        upgrade_from("1001")

        behaviors = types["UserProfile"].behaviors
        assert "pas.plugins.identity.email_addresses" in behaviors
        assert "pas.plugins.identity.profile_details" in behaviors
