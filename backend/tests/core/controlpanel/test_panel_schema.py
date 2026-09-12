"""What the settings panel serves, and how it is laid out.

Both are behaviour somebody sees. The frontend renders the settings form from
the schema this panel serves -- ``ProvidersControlPanel.tsx`` passes it
straight to Volto's ``Form`` -- and Volto reads ``schema.fieldsets`` on the
first render, so a fieldset here is a tab there and the order of the fieldsets
is the order of the tabs.

Before this, the panel named :class:`IIdentitySettings` alone and declared no
fieldsets at all: thirteen fields in one flat column, and the thirteen records
of :class:`IProfileSettings` -- where principals are filed, which of their
states count, what a profile must carry -- reachable only through the generic
registry editor.
"""

from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.controlpanel.controlpanel import IdentityConfigletPanel
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityPanelSchema
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from plone import api
from plone.registry.interfaces import IRegistry
from plone.restapi.deserializer.controlpanels import ControlpanelDeserializeFromJson
from plone.restapi.serializer.controlpanels import ControlpanelSerializeToJson
from zope.component import getUtility
from zope.schema import getFieldNames

import json
import pytest


#: The form, tab by tab: id, label, and the fields on it in order. Written out
#: rather than derived, because it is the thing being asserted -- a field added
#: to either schema and named in no fieldset lands silently on the first tab,
#: and only a statement of what the tabs *are* catches that.
TABS = [
    ("default", "Login", ["callback_url", "discovery_timeout"]),
    (
        "portraits",
        "Portraits",
        ["sync_portraits", "portrait_timeout", "portrait_max_bytes"],
    ),
    (
        "audit",
        "Audit log",
        ["audit_max_entries", "audit_max_days", "audit_record_pii", "audit_sinks"],
    ),
    (
        "containers",
        "Where principals are filed",
        [
            "profile_container_parent",
            "profile_container_id",
            "profile_container_title",
            "profile_container_type",
            "group_container_parent",
            "group_container_id",
            "group_container_title",
            "group_container_type",
        ],
    ),
    (
        "states",
        "Which states count",
        ["profile_enumeration_states", "group_enumeration_states"],
    ),
    (
        "gate",
        "The profile gate",
        [
            "enforce_required_profile_fields",
            "confirm_email_at_first_login",
            "required_profile_fields",
            "gate_exempt_paths",
        ],
    ),
]

#: Declared read-only, so on no tab and in no panel save. See
#: :class:`TestTheDerivedRecordsAreNotEditedHere`.
DERIVED = frozenset({
    "user_content_type",
    "user_container_path",
    "group_content_type",
    "group_container_path",
})


class TestTheFormIsGrouped:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request

    def payload(self) -> dict:
        """Return what ``@controlpanels/identity-providers`` answers.

        :returns: The serialized panel.
        """
        panel = IdentityConfigletPanel(self.portal, self.request)
        # The serializer builds the panel's ``@id`` from ``__name__``, which
        # the publisher sets while traversing and nothing sets here.
        panel.__name__ = CONFIGLET_ID
        return ControlpanelSerializeToJson(panel)()

    def test_the_tabs(self):
        """Order included: Volto renders them in the order they arrive, and
        the order is a consequence of the base order of the panel schema,
        which is exactly the kind of thing a tidy-up reverses."""
        served = [
            (fieldset["id"], fieldset["title"], fieldset["fields"])
            for fieldset in self.payload()["schema"]["fieldsets"]
        ]

        assert served == TABS

    def test_every_field_is_on_a_tab(self):
        """Stated against the schemas rather than against ``TABS``, so the
        two cannot drift together: a field added to either interface is on a
        tab or this fails. The derived records are the exception, and
        they are named."""
        declared = (
            set(getFieldNames(IIdentitySettings)) | set(getFieldNames(IProfileSettings))
        ) - DERIVED
        on_a_tab = {field for _id, _label, fields in TABS for field in fields}

        assert on_a_tab == declared

    def test_the_panel_serves_both_schemas(self):
        """The point of serving a derived schema at all: twenty-two
        properties, which is all twenty-six fields but the four derived
        records."""
        properties = self.payload()["schema"]["properties"]

        assert (
            set(properties)
            == (
                set(getFieldNames(IIdentitySettings))
                | set(getFieldNames(IProfileSettings))
            )
            - DERIVED
        )

    def test_the_profile_settings_arrive_with_their_values(self):
        """A schema an operator can see but not fill in would be worse than
        the registry editor, so the data half is asserted too."""
        data = self.payload()["data"]

        assert data["profile_container_id"] == "identity-profiles"
        assert data["enforce_required_profile_fields"] is True
        assert data["profile_enumeration_states"] == ["incomplete", "complete"]


class TestTheCombinedSchemaAddressesRealRecords:
    """The derived interface is not a new set of records.

    Both bases register under the same ``pas.plugins.identity`` prefix and
    share no field name, so ``forInterface`` resolves all twenty-six against
    records the profile already created. Nothing about that is obvious from
    reading the class, hence these.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.proxy = getUtility(IRegistry).forInterface(
            IIdentityPanelSchema, prefix="pas.plugins.identity"
        )

    def test_reading_reaches_both_halves(self):
        """One proxy, and the two schemas answer through it."""
        assert self.proxy.callback_url == "/login-identity"
        assert self.proxy.profile_container_id == "identity-profiles"

    def test_writing_lands_on_the_record_the_package_reads(self):
        """The half that matters: the panel writes through this proxy, and
        the rest of the package reads the record by name. A prefix that did
        not line up would write somewhere nothing looks."""
        self.proxy.profile_container_title = "People"

        assert (
            api.portal.get_registry_record(
                "pas.plugins.identity.profile_container_title"
            )
            == "People"
        )

    def test_the_two_schemas_share_no_field_name(self):
        """What makes one prefix safe for both. A collision would have one
        field shadow the other on the panel, with no error anywhere."""
        assert not set(getFieldNames(IIdentitySettings)) & set(
            getFieldNames(IProfileSettings)
        )


class TestTheDerivedRecordsAreNotEditedHere:
    """The four records core reads, derived from the container settings.

    Taking them off the form was not enough. The panel serves every schema
    field in ``data``, the frontend's form submits that object back whole,
    and the derived fields were written after the container settings they
    come from -- so moving the container wrote the old paths back over the
    ones just derived, and users went on being created in the folder the
    operator had moved away from. Read-only fields are skipped by a panel
    save, which is what these hold the schema to.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request

    def panel(self) -> IdentityConfigletPanel:
        """Return the panel, named as the publisher would name it.

        :returns: The configlet panel.
        """
        panel = IdentityConfigletPanel(self.portal, self.request)
        panel.__name__ = CONFIGLET_ID
        return panel

    def save(self, data: dict) -> None:
        """Save through the panel, as ``PATCH @controlpanels`` does.

        :param data: The request body.
        """
        self.request["BODY"] = json.dumps(data)
        ControlpanelDeserializeFromJson(self.panel())()

    def test_they_are_not_on_the_form(self):
        properties = ControlpanelSerializeToJson(self.panel())()["schema"]["properties"]

        assert not set(DERIVED) & set(properties)

    def test_saving_the_whole_form_keeps_them_in_step(self):
        """What the frontend sends: everything it was served, with one field
        changed."""
        data = ControlpanelSerializeToJson(self.panel())()["data"]
        data["profile_container_id"] = "people"

        self.save(data)

        assert (
            api.portal.get_registry_record("pas.plugins.identity.user_container_path")
            == "people"
        )

    def test_a_save_naming_one_writes_nothing(self):
        """Not only our frontend: any client may send the field."""
        self.save({"user_content_type": "Document"})

        assert (
            api.portal.get_registry_record("pas.plugins.identity.user_content_type")
            == "UserProfile"
        )
