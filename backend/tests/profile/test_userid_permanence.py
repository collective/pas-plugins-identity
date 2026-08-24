"""``userid`` is permanent, and ``email`` is required.

The userid is what an identity record, every local role granted on a Profile
and the catalog entry the enumeration plugin queries all point at. Rewriting
it detaches all three at once and leaves a Profile that still looks correct,
which is why the refusal has to exist on every path a field can be written
through rather than only in the form a person sees.

Until this landed the type's own docstring claimed the edit form marked it
read-only. It did not: there was no such directive anywhere, and a PATCH
changed it without complaint.
"""

from . import PROFILE_ID
from pas.plugins.identity.profile.content.profile import IProfileSchema
from pas.plugins.identity.profile.deserializer import UseridIsPermanent
from plone.restapi.interfaces import IDeserializeFromJson
from z3c.form.interfaces import IEditForm
from zope.component import getMultiAdapter

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def body(request, payload: dict):
    """Put a JSON body on the request.

    :param request: The request to write to.
    :param payload: What the caller submitted.
    """
    request["BODY"] = json.dumps(payload).encode()
    return request


class TestUseridIsPermanent:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.request = portal.REQUEST
        self.profile = make_profile("alice", email="alice@example.com")

    def deserialize(self, payload: dict):
        """Apply a PATCH body to the Profile, as plone.restapi would.

        :param payload: The submitted fields.
        :returns: Whatever the deserializer returns.
        """
        deserializer = getMultiAdapter(
            (self.profile, self.request), IDeserializeFromJson
        )
        return deserializer(validate_all=False)

    def test_a_changed_userid_is_refused(self):
        """The whole point: it may not be rewritten over the API."""
        body(self.request, {"userid": "bob"})

        with pytest.raises(Exception) as caught:
            self.deserialize({})

        assert "userid" in str(caught.value) or isinstance(
            caught.value, UseridIsPermanent
        )
        assert self.profile.userid == "alice"

    def test_the_same_userid_is_accepted(self):
        """A form round-trip echoes every field back.

        Refusing that would make the field impossible to *send* rather than
        impossible to *change*, which breaks every client that PATCHes the
        object it just read.
        """
        body(self.request, {"userid": "alice", "fullname": "Alice Liddell"})

        self.deserialize({})

        assert self.profile.userid == "alice"
        assert self.profile.fullname == "Alice Liddell"

    def test_another_text_line_is_untouched(self):
        """The deserializer is registered for every text line on the type,
        because that is the narrowest registration there is. Everything but
        ``userid`` has to behave exactly as the default did."""
        body(self.request, {"location": "Oxford"})

        self.deserialize({})

        assert self.profile.location == "Oxford"

    def test_the_edit_form_does_not_offer_it(self):
        """The path a person with a browser takes."""
        modes = IProfileSchema.queryTaggedValue("plone.autoform.modes", ())

        assert (IEditForm, "userid", "display") in modes

    def test_the_add_form_still_asks(self):
        """Creation is the one moment the answer is not yet decided, so the
        mode is scoped to the edit form rather than the field."""
        modes = IProfileSchema.queryTaggedValue("plone.autoform.modes", ())

        assert [m for m in modes if m[1] == "userid"] == [
            (IEditForm, "userid", "display")
        ]


class TestEmailIsRequired:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_field_is_required(self):
        """A Profile exists to be the thing a person is reached and
        recognised by; the enumeration plugin, the property map and the
        magic-link join all read the address."""
        assert IProfileSchema["email"].required is True
