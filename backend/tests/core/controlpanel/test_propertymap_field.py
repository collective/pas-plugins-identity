"""What the property map's target field is, and what that reaches.

Three things used to answer "which field may a map write" separately: a
login, a principal document, and the control panel, which answered nothing at
all and took free text. So a map could name ``email`` or ``portrait`` -- both
member fields, both handled by this package, neither written through a map --
and the row was stored, exported, and dropped on every login without a word.

The target is a ``Choice`` now. These assert the three consequences: the
registry refuses such a row, the served schema carries the vocabulary a picker
is built from, and the check an operator's edit goes through says which row is
wrong.
"""

from pas.plugins.identity.core.controlpanel import check_propertymap
from pas.plugins.identity.core.controlpanel import InvalidPropertyMap
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel.interfaces import IProviderRecords
from pas.plugins.identity.core.services.schema import jsonschema_for
from pas.plugins.identity.core.utils.propertymap import MAPPABLE_FIELDS
from pas.plugins.identity.core.vocabularies.userfields import USER_FIELDS_VOCABULARY
from zope.schema.interfaces import IChoice

import pytest


class TestTheFieldItself:
    """Read off the interface, so a change back to free text is a red test
    rather than a silently permissive form."""

    def test_the_target_is_a_choice(self):
        assert IChoice.providedBy(IProviderRecords["propertymap"].value_type)

    def test_over_this_package_s_vocabulary(self):
        value_type = IProviderRecords["propertymap"].value_type

        assert value_type.vocabularyName == USER_FIELDS_VOCABULARY

    def test_the_claim_side_stays_free_text(self):
        """A claim path is whatever the far end publishes, and nothing here
        can enumerate it."""
        key_type = IProviderRecords["propertymap"].key_type

        assert not IChoice.providedBy(key_type)


class TestTheRegistryRefusesADeadRow:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def _store(self, propertymap: dict) -> None:
        """Store one provider carrying this map.

        :param propertymap: The map to store.
        """
        set_providers([
            ProviderConfig(
                provider_id="github",
                driver_id="github",
                title="GitHub",
                propertymap=propertymap,
            )
        ])

    def test_a_usable_row_is_stored(self):
        self._store({"bio": "description"})

    @pytest.mark.parametrize(
        "field", ["email", "portrait", "login", "group_ids", "username"]
    )
    def test_a_row_naming_anything_else_is_refused(self, field: str):
        with pytest.raises(InvalidPropertyMap):
            self._store({"claim": field})

    def test_the_refusal_names_the_row_and_the_alternatives(self):
        """An operator reading it has to know what to type instead. The
        registry's own refusal is ``WrongContainedType([...])``, which names
        neither."""
        with pytest.raises(InvalidPropertyMap) as caught:
            check_propertymap({"picture": "portrait"})

        message = str(caught.value)
        assert "portrait" in message
        for name in MAPPABLE_FIELDS:
            assert name in message


class TestWhatTheEndpointServes:
    """The frontend builds the picker from this and nothing else."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.schema = jsonschema_for(IProviderRecords, portal, request_)
        self.propertymap = self.schema["properties"]["propertymap"]

    def test_the_map_is_served_as_a_dict(self):
        assert self.propertymap["type"] == "dict"

    def test_the_value_carries_the_vocabulary(self):
        """A named vocabulary is served as a URL rather than inline terms,
        which is what the ``@vocabularies`` request in the form follows."""
        vocabulary = self.propertymap["value_type"]["additional"]["vocabulary"]

        assert vocabulary["@id"].endswith(f"/@vocabularies/{USER_FIELDS_VOCABULARY}")

    def test_the_key_carries_no_vocabulary(self):
        assert "vocabulary" not in self.propertymap["key_type"]["additional"]
