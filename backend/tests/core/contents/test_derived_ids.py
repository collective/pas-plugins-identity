"""``userid`` and ``group_id`` are the object's own id.

They used to be stored fields *and* the id the object is filed under, with
nothing keeping the two equal. Different code read different ones -- the PAS
plugin traverses ``container.get(userid)`` while the catalog indexes the
field -- so a rename left enumeration working and every write addressed to
nothing at all. Deriving one from the other is what makes that state
unreachable.

Renaming is deliberately still allowed, and the principal id follows the new
name. That is a decision rather than a consequence: stored identities, local
roles and sharing entries all name the old id and do not follow.
"""

from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.contents.group import IUserGroupSchema
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from plone import api

import pytest


class TestTheFieldIsGone:
    def test_userid_is_not_a_schema_field(self):
        """No form offers it and no deserializer can write it, which is what
        makes the property the only way in."""
        assert "userid" not in IUserProfileSchema.names()

    def test_group_id_is_not_a_schema_field(self):
        """The same, for groups."""
        assert "group_id" not in IUserGroupSchema.names()


class TestDerivedFromTheId:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile, make_group) -> None:
        self.portal = portal
        self.profile = make_profile("alice")
        self.group = make_group("editors")

    def test_userid_is_the_object_id(self):
        """The whole point."""
        assert self.profile.userid == self.profile.getId() == "alice"

    def test_group_id_is_the_object_id(self):
        """And for groups."""
        assert self.group.group_id == self.group.getId() == "editors"

    def test_a_matching_write_is_harmless(self):
        """Dexterity's factory setattrs every keyword it is handed, and every
        payload exported before this became derived still carries the key.
        Refusing those would turn a correct value into a failed import."""
        self.profile.userid = "alice"

        assert self.profile.userid == "alice"

    def test_a_disagreeing_write_does_not_take(self):
        """Somebody trying to reassign a principal. It cannot work, and the
        object does not pretend otherwise."""
        self.profile.userid = "mallory"

        assert self.profile.userid == "alice"

    def test_a_disagreeing_group_write_does_not_take(self):
        """The same, for groups."""
        self.group.group_id = "administrators"

        assert self.group.group_id == "editors"

    def test_the_catalog_agrees_with_the_object(self):
        """Enumeration reads the catalog and the plugin traverses by id; the
        bug this replaces was those two disagreeing."""
        catalog = query_catalog()

        brains = catalog(userid="alice")

        assert [b.userid for b in brains] == ["alice"]


class TestRenaming:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.container = portal["identity-profiles"]
        make_profile("alice")

    def test_the_userid_follows_the_new_name(self):
        """Chosen deliberately over refusing the rename. The consequence is
        real and is not softened anywhere: what the old id was written into
        -- identity records, local roles, sharing entries -- still says
        ``alice``."""
        api.content.rename(obj=self.container["alice"], new_id="alice-2")

        assert self.container["alice-2"].userid == "alice-2"

    def test_the_catalog_follows_too(self):
        """A rename is a move, and the catalog is kept by the move
        subscribers rather than by anything the field did."""
        api.content.rename(obj=self.container["alice"], new_id="alice-2")

        catalog = query_catalog()
        assert [b.userid for b in catalog(userid="alice-2")] == ["alice-2"]
        assert len(catalog(userid="alice")) == 0
