"""``PrincipalsContainer`` -- the folder principals are filed in.

What the FTI declares. What a container does once it exists -- its order, its
first block, the refusal when a parent will not take it -- is tested beside
the code that creates it, in ``tests/core/test_container.py``.
"""

from pas.plugins.identity.core.container import CONTAINER_PORTAL_TYPE
from plone.dexterity.fti import DexterityFTI

import pytest


@pytest.fixture(scope="class")
def portal_type() -> str:
    """Return the type under test.

    :returns: The portal type id.
    """
    return CONTAINER_PORTAL_TYPE


class TestTheFTI:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, portal_type: str, get_fti) -> None:
        self.fti: DexterityFTI = get_fti(portal_type)

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("title", "Principals folder"),
            (
                "klass",
                "pas.plugins.identity.core.contents.principals.PrincipalsContainer",
            ),
            (
                "schema",
                "pas.plugins.identity.core.contents.principals."
                "IPrincipalsContainerSchema",
            ),
            ("global_allow", True),
            ("filter_content_types", True),
            ("add_permission", "pas.plugins.identity.principalscontainer.add"),
        ],
    )
    def test_fti(self, attr: str, expected):
        assert isinstance(self.fti, DexterityFTI)
        assert getattr(self.fti, attr) == expected

    def test_it_takes_principals_and_nothing_else(self):
        """Which of the two a given container takes is the add permission's
        answer, granted for the kind the registry files there."""
        assert tuple(self.fti.allowed_content_types) == ("UserProfile", "UserGroup")

    @pytest.mark.parametrize(
        "idx,behavior",
        enumerate((
            "plone.basic",
            "plone.excludefromnavigation",
            "volto.blocks",
        )),
    )
    def test_behaviors(self, idx: int, behavior: str):
        """Present, and in this order."""
        assert self.fti.behaviors[idx] == behavior

    def test_no_other_behaviors(self):
        """The list above is the whole list. ``plone.shortname`` is not on it:
        the registry names the container by its id, so a rename would leave
        the records pointing at nothing."""
        assert len(self.fti.behaviors) == 3
