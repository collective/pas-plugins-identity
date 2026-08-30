"""What an export contains, and what it must never contain.

The round-trip test says the document is *sufficient*. This one says it is not
excessive: a document is a file that gets copied to a laptop, attached to a
ticket and left in a bucket, and the interesting question about it is what an
operator has handed out by producing one.
"""

from . import CLAIMS
from . import PROVIDER
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import validate

import json
import pytest


class TestWhatAnExportSays:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_user, make_group) -> None:
        self.portal = portal
        self.plugin = plugin
        make_group("site-editors", title="Site Editors")
        self.profile = make_user(location="Berlin", group_ids=("site-editors",))
        self.plugin.link(USERID, PROVIDER, SUBJECT, CLAIMS)

    def test_the_document_validates(self):
        """The exporter and the validator have to agree, or a document this
        package wrote is one it will not read back."""
        assert validate(export_site()) is not None

    def test_it_carries_its_version(self):
        """A reader from the future needs to know what it is looking at."""
        assert export_site()["version"] == DOCUMENT_VERSION

    def test_the_identity_join_is_in_it(self):
        """``plone.exportimport`` moves the content; this is the part it
        cannot know about."""
        identities = export_site()["users"][0]["identities"]

        assert (identities[0]["provider"], identities[0]["subject"]) == (
            PROVIDER,
            SUBJECT,
        )

    def test_timestamps_are_strings(self):
        """They are ``datetime`` objects in the store, and a document has to
        survive ``json.dumps``."""
        identity = export_site()["users"][0]["identities"][0]

        assert isinstance(identity["created"], str)

    def test_it_names_the_site_it_came_from(self):
        assert export_site()["site"] == self.portal.getId()


class TestWhatAnExportMustNotSay:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_user) -> None:
        self.portal = portal
        self.plugin = plugin
        self.profile = make_user()
        self.plugin.link(USERID, PROVIDER, SUBJECT, CLAIMS)

    def test_no_password_hash_leaves_the_site(self):
        """A Profile can carry a credential in an annotation, through the
        password behavior. A document is a file that gets copied around and
        the one thing it must never be is a way in.

        The storage is constructed directly rather than adapted, because the
        behavior is not enabled on this site and the question here is about
        the *exporter*: whatever put a hash on the object, it must not come
        out in the document.
        """
        from pas.plugins.identity.core.behaviors.password import PasswordStorage

        PasswordStorage(self.profile).set_password("a-real-password")

        serialized = json.dumps(export_site())

        assert "a-real-password" not in serialized
        assert "{SSHA}" not in serialized
        assert "hash" not in serialized

    def test_no_audit_entry_leaves_the_site(self):
        """A login history, with an IP address on a site that opted in. It is
        read where it lives, under a permission."""
        self.plugin.audit.record(USERID, "authenticated", PROVIDER, True)

        assert "authenticated" not in json.dumps(export_site())

    def test_no_provider_secret_leaves_the_site(self):
        """Provider configuration is not in the document at all, which is the
        strongest form of not exporting a client secret."""
        document = export_site()

        assert "providers" not in document
        assert "client_secret" not in json.dumps(document)


class TestOnASiteWithoutTheAddOn:
    def test_it_refuses_rather_than_writing_an_empty_document(self, portal, make_user):
        """An empty document that looks like a backup is worse than an error:
        it is discovered at restore time, which is the worst moment."""
        make_user()
        portal.acl_users._delObject(CORE_PLUGIN_ID)

        with pytest.raises(ExportImportError) as error:
            export_site()

        assert "no identity plugin" in str(error.value)
