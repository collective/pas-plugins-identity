"""The identity provider's demo group.

The demo shipped a user and no group, so the one thing a content-backed group
demonstrates -- that a site can have groups without ``source_groups`` -- was
never on screen. What is asserted here is the *demo's* wiring, not the
plugin's: ``tests/profile/test_groups.py`` already pins what a content-backed
group does once it exists. This pins that the provider actually gets one, that
belonging to it carries a role, and that a second run against a warm volume
changes nothing.

The profile is applied per test through ``@pytest.mark.portal`` rather than by
installing ``identitydemo``, which would drag in a published client secret and
the demo user's password for a question that needs neither.
"""

from identitydemo import settings
from identitydemo.setuphandlers.idp import _create_demo_group
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.profile.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.profile.container import get_container
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import pytest


pytestmark = pytest.mark.portal(profiles=[f"{PACKAGE_NAME}:profile"])


@pytest.fixture(autouse=True)
def _manager(integration):
    """Run as a site manager, before the marker applies the profile.

    Bound to ``integration`` rather than to ``portal`` deliberately: the
    marker applies profiles as whoever is logged in, and it grants its own
    ``roles`` argument afterwards, which is too late for the install step.

    :param integration: The integration layer.
    """
    setRoles(integration["portal"], TEST_USER_ID, ["Manager"])


class TestDemoGroup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, _manager) -> None:
        self.portal = portal
        get_container(create=True)
        api.user.create(
            username=settings.DEMO_USER_ID,
            email=settings.DEMO_USER_EMAIL,
            password=settings.DEMO_USER_PASSWORD,
            properties={"fullname": settings.DEMO_USER_FULLNAME},
        )

    def group(self):
        """Return the demo group, as PAS answers for it.

        :returns: The group, or ``None``.
        """
        return api.group.get(groupname=settings.DEMO_GROUP_ID)

    def test_the_group_exists(self):
        """The demo has one now."""
        _create_demo_group()

        assert self.group() is not None

    def test_the_group_is_content(self):
        """The whole claim. A ``source_groups`` row would satisfy
        ``api.group.get`` just as well, which is what makes asserting on the
        object rather than on the lookup the only honest test here."""
        _create_demo_group()

        container = get_container()
        obj = container[settings.DEMO_GROUP_ID]
        assert obj.portal_type == GROUP_PORTAL_TYPE
        assert IGroupContent.providedBy(obj)

    def test_the_group_lives_beside_the_profiles(self):
        """Groups and Profiles share one container, so nothing had to be
        configured for this beyond what the demo user already needed."""
        _create_demo_group()

        assert settings.DEMO_GROUP_ID in get_container().objectIds()

    def test_it_carries_its_title(self):
        """What a reader sees in the group listing."""
        _create_demo_group()

        assert self.group().getProperty("title") == settings.DEMO_GROUP_TITLE

    def test_belonging_to_it_grants_the_role(self):
        """A group with no role would demonstrate that groups can exist,
        which is not the interesting claim."""
        _create_demo_group()

        assert set(settings.DEMO_GROUP_ROLES) <= set(
            api.group.get_roles(group=self.group())
        )

    def test_the_demo_user_is_a_member(self):
        """Through the Profile: ``addPrincipalToGroup`` writes ``group_ids``
        on the member, because that is the direction the question is asked
        in."""
        _create_demo_group()

        user = api.user.get(userid=settings.DEMO_USER_ID)
        assert settings.DEMO_GROUP_ID in {
            group.getId() for group in api.group.get_groups(user=user)
        }

    def test_the_user_really_has_the_role(self):
        """The point of the whole arrangement, and not implied by the two
        assertions above: a role on the group and a membership record are
        only worth something if PAS adds them up."""
        _create_demo_group()

        user = api.user.get(userid=settings.DEMO_USER_ID)
        assert set(settings.DEMO_GROUP_ROLES) <= set(api.user.get_roles(user=user))

    def test_running_it_again_changes_nothing(self):
        """A warm volume re-runs the profile, and the group must not be
        duplicated, re-granted or re-joined."""
        _create_demo_group()
        _create_demo_group()

        user = api.user.get(userid=settings.DEMO_USER_ID)
        member_of = [group.getId() for group in api.group.get_groups(user=user)]
        assert member_of.count(settings.DEMO_GROUP_ID) == 1
        assert len(get_container().objectIds()) == len(set(get_container().objectIds()))

    def test_it_survives_a_missing_demo_user(self):
        """The group is created before anything is known about the user, and
        a site whose adder declined must still get the group rather than an
        exception halfway through the install."""
        api.user.delete(username=settings.DEMO_USER_ID)

        _create_demo_group()

        assert self.group() is not None
