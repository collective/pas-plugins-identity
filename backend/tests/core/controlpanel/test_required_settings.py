"""The settings nothing works without are required, and required means non-empty.

``required=True`` is half of it. ``zope.schema`` checks a required value
against ``missing_value``, which is ``None`` for every field here, so an empty
tuple and a zero both pass a field that is merely required. The two state
lists carry ``min_length=1`` and the timeout ``min=1`` for that reason, and
these tests ask the fields themselves rather than trusting the flag.
"""

from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.controlpanel.controlpanel import IdentityConfigletPanel
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from plone import api
from plone.restapi.deserializer.controlpanels import ControlpanelDeserializeFromJson
from zExceptions import BadRequest
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import TooShort
from zope.schema.interfaces import TooSmall

import json
import pytest


REQUIRED = [
    pytest.param(IIdentitySettings, "callback_url", id="callback_url"),
    pytest.param(IIdentitySettings, "discovery_timeout", id="discovery_timeout"),
    pytest.param(
        IProfileSettings, "profile_enumeration_states", id="profile_enumeration_states"
    ),
    pytest.param(
        IProfileSettings, "group_enumeration_states", id="group_enumeration_states"
    ),
]


class TestTheFieldsRefuseEmptiness:
    @pytest.mark.parametrize("schema,name", REQUIRED)
    def test_nothing_is_refused(self, schema, name: str):
        assert schema[name].required is True
        with pytest.raises(RequiredMissing):
            schema[name].validate(None)

    @pytest.mark.parametrize(
        "name", ["profile_enumeration_states", "group_enumeration_states"]
    )
    def test_an_empty_list_of_states_is_refused(self, name: str):
        """What ``required`` alone lets through. No state counting would hide
        every principal of that kind."""
        with pytest.raises(TooShort):
            IProfileSettings[name].validate(())

    @pytest.mark.parametrize("value", [0, -1])
    def test_a_timeout_under_a_second_is_refused(self, value: int):
        """Zero is what ``required`` alone lets through."""
        with pytest.raises(TooSmall):
            IIdentitySettings["discovery_timeout"].validate(value)

    @pytest.mark.parametrize(
        "schema,name,value",
        [
            pytest.param(
                IIdentitySettings, "callback_url", "/login-identity", id="path"
            ),
            pytest.param(IIdentitySettings, "discovery_timeout", 1, id="one-second"),
            pytest.param(
                IProfileSettings,
                "group_enumeration_states",
                ("active",),
                id="one-state",
            ),
        ],
    )
    def test_the_smallest_real_value_is_accepted(self, schema, name: str, value):
        """The floor is where it says, not one step above it."""
        schema[name].validate(value)


class TestThePanelRefusesThem:
    """The panel validates a save against these fields, so a rule on the field
    is a rule at the API as well. That includes a blank callback URL, which
    the text deserializer strips to ``None`` before the field sees it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request

    def save(self, data: dict) -> None:
        """Save through the panel, as ``PATCH @controlpanels`` does.

        :param data: The request body.
        """
        self.request["BODY"] = json.dumps(data)
        panel = IdentityConfigletPanel(self.portal, self.request)
        panel.__name__ = CONFIGLET_ID
        ControlpanelDeserializeFromJson(panel)()

    @pytest.mark.parametrize(
        "name,value,stored",
        [
            pytest.param("callback_url", "", "/login-identity", id="empty-callback"),
            pytest.param("callback_url", "   ", "/login-identity", id="blank-callback"),
            pytest.param("discovery_timeout", 0, 10, id="zero-timeout"),
            pytest.param(
                "profile_enumeration_states",
                [],
                ("incomplete", "complete"),
                id="no-profile-states",
            ),
            pytest.param(
                "group_enumeration_states", [], ("active",), id="no-group-states"
            ),
        ],
    )
    def test_an_empty_value_is_refused_and_not_stored(self, name: str, value, stored):
        with pytest.raises(BadRequest):
            self.save({name: value})

        assert api.portal.get_registry_record(f"pas.plugins.identity.{name}") == stored
