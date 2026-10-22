"""A property map writing a behavior's field, through a real login (#143)."""

from . import CLAIMS
from . import DEX_IDENTITY
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.profiles import get_profile
from tests.extra_profile_fields import IAnnotatedProfileFields

import copy
import logging
import pytest


PROVIDER, SUBJECT = DEX_IDENTITY

#: The claim ``id.plone.org`` releases, in the shape of the field it fills.
SOCIAL_LINKS = [
    {
        "@id": "github",
        "id": "github",
        "title": "GitHub",
        "href": [{"@id": "https://github.com/example", "title": "GitHub"}],
    },
]


def structured_claims(**raw) -> dict:
    """Return claims carrying structured values, fresh for each login.

    Fresh, because a login that kept a reference to the claims would share a
    list with the next one, and a test of what is copied would prove nothing.

    :param raw: Raw claims to use instead of the defaults.
    :returns: The claims.
    """
    defaults = {
        "social_links": SOCIAL_LINKS,
        "tags": ["plone", "python"],
        "age": 42,
        "address": {"formatted": "São Paulo"},
    }
    return {**CLAIMS, "raw": copy.deepcopy(raw or defaults)}


def configure(propertymap: dict[str, str]) -> None:
    """Store the Dex provider with a property map.

    :param propertymap: Claim path to user field.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            propertymap=propertymap,
        )
    ])


class TestABehaviorFieldOnLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, extra_profile_fields, plugin) -> None:
        self.portal = extra_profile_fields
        self.plugin = plugin

    def authenticate(self, claims=None):
        """Run a login and return the Profile it left behind.

        :param claims: Claims to authenticate with; :func:`structured_claims`
            when omitted.
        :returns: The Profile.
        """
        claims = claims or structured_claims()
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": claims,
        })
        return get_profile(userid)

    def test_a_list_of_mappings_is_written_as_sent(self):
        """The case the issue was opened for: the claim already has the
        field's shape, so a row in the map is all it takes."""
        configure({"social_links": "social_links"})

        assert self.authenticate().social_links == SOCIAL_LINKS

    def test_a_list_reaches_a_tuple_field_as_a_tuple(self):
        """JSON has no tuple, and the field would refuse a list."""
        configure({"tags": "tags"})

        assert self.authenticate().tags == ("plone", "python")

    def test_a_number_reaches_a_number_field(self):
        configure({"age": "age"})

        assert self.authenticate().age == 42

    def test_a_value_the_field_refuses_is_not_written(self, caplog):
        """Logged and skipped: one bad row does not cost the login."""
        configure({"social_links": "age"})

        with caplog.at_level(logging.WARNING):
            profile = self.authenticate()

        assert profile.age is None
        assert "Not writing claim 'social_links' to 'age'" in caplog.text

    def test_the_other_rows_are_still_written(self):
        configure({"social_links": "age", "tags": "tags"})

        assert self.authenticate().tags == ("plone", "python")

    def test_a_text_field_still_reads_a_mapping_as_absent(self):
        """``address`` is an object at every OIDC provider, and a repr of it
        is not somebody's location."""
        configure({"address": "location"})

        assert not self.authenticate().location

    def test_a_later_login_updates_what_the_provider_wrote(self):
        configure({"social_links": "social_links"})
        self.authenticate()

        moved = [{**SOCIAL_LINKS[0], "title": "GitHub (moved)"}]
        profile = self.authenticate(structured_claims(social_links=moved))

        assert profile.social_links == moved

    def test_an_edit_survives_the_next_login(self):
        """The ownership fence, asked of a list rather than a line of text."""
        configure({"social_links": "social_links"})
        profile = self.authenticate()
        profile.social_links = []

        assert self.authenticate().social_links == []

    def test_what_is_remembered_is_not_the_field_s_own_list(self):
        """Changing the list in place would otherwise change the remembered
        value with it, and the provider would still own an edited field."""
        configure({"social_links": "social_links"})
        profile = self.authenticate()
        profile.social_links.append({"id": "mastodon", "title": "Mastodon"})

        assert len(self.authenticate().social_links) == 2

    def test_a_field_stored_by_a_factory_is_written_through_it(self):
        """A behavior may keep its value in an annotation; an attribute set
        on the object would be one nothing reads."""
        configure({"nickname": "nickname"})

        profile = self.authenticate(structured_claims(nickname="ada"))

        assert IAnnotatedProfileFields(profile).nickname == "ada"

    def test_an_edit_through_the_factory_survives_the_next_login(self):
        configure({"nickname": "nickname"})
        profile = self.authenticate(structured_claims(nickname="ada"))
        IAnnotatedProfileFields(profile).nickname = "Ada"

        profile = self.authenticate(structured_claims(nickname="ada"))

        assert IAnnotatedProfileFields(profile).nickname == "Ada"
