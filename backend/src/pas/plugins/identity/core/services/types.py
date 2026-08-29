"""``@types`` for the user type, with the site's required fields in it.

``plone.restapi`` builds the ``required`` list of a type's JSON schema from
``field.required`` and from nothing else. That is the right answer for
ordinary content and the wrong one here, because
``pas.plugins.identity.required_profile_fields`` can require a field the type
leaves optional -- a site that wants a full name should not have to make
``fullname`` schema-required, which would also make it mandatory for
``api.user.create`` and for every import.

Without this the two halves disagree in the worst possible direction. The flow
holds a profile ``incomplete`` until ``fullname`` is filled in; the edit form,
built from this schema, does not ask for it and accepts a save without it. The
user saves, the profile is still incomplete, and they are sent back to the
same form. A loop, produced by a registry record and nothing else.

So the service adds what the site requires to what the type requires. It does
not remove anything: a field the type marks required stays required whatever
the record says, because the type is the one that cannot store an empty value.

**It also answers the address question.** A provider that offered several
addresses had none of them chosen -- see
:mod:`pas.plugins.identity.core.emailchoices` -- so the profile arrives
without one and the gate holds its owner on this form. Asking them to retype
an address the site was handed a list of would be a poor way to end that, so
while ``emails`` is still empty the schema carries the offered addresses on
that field's ``items`` and Volto renders a choice instead of an empty box.

``emails`` rather than ``email``, since the address became a list: the person
picks which of the offered addresses are theirs, and possibly more than one.
``email`` is derived and read-only, so there is no box on it to fill.

Advisory rather than binding, and deliberately: the entries are still plain
addresses, so a ``PATCH`` carrying one that was never offered is accepted.
The list is what the person was handed, not the set of addresses they are
allowed to have.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.completeness import configured_fields
from pas.plugins.identity.core.emailchoices import offered_addresses
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api
from plone.api.exc import InvalidParameterError
from plone.restapi.services.types.get import TypesGet


def user_content_type() -> str:
    """Return the portal type this site keeps its users in.

    Read from core's record rather than assumed, so a site running its own
    user type gets its own form corrected rather than ours.

    :returns: A portal type id.
    """
    try:
        configured = api.portal.get_registry_record(
            USER_CONTENT_TYPE_RECORD, default=""
        )
    except InvalidParameterError:
        configured = ""
    return configured or PROFILE_PORTAL_TYPE


class ProfileTypesGet(TypesGet):
    """``@types``, with the site's required profile fields added."""

    def __init__(self, context, request) -> None:
        """Bind the service to its context and request.

        ``TypesGet.__init__`` calls ``super().__init__(context, request)``
        and the chain above it ends at ``object``: ``plone.rest`` injects
        those attributes through the class it publishes rather than through
        an ``__init__``, so the factory class on its own cannot be
        constructed and cannot be tested without standing up the publisher.
        Same reason and same fix as
        :class:`~pas.plugins.identity.core.services.base.IdentityService`.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        self.context = context
        self.request = request
        self.params = []

    def reply_for_type(self):
        """Return the type's JSON schema, with ``required`` corrected.

        :returns: The schema, or whatever the base class answered when it is
            not a schema for the user type.
        """
        # The base class pops the type name off ``params``, so it has to be
        # read before calling up rather than after.
        portal_type = self.params[0] if self.params else ""
        schema = super().reply_for_type()

        if portal_type != user_content_type():
            return schema
        if not isinstance(schema, dict) or "required" not in schema:
            # A 404 body, or a shape a future plone.restapi answers with.
            return schema

        required = list(schema["required"])
        properties = schema.get("properties") or {}
        for name in configured_fields():
            # Only a field the form actually renders. Naming one that is not
            # on the type is a configuration mistake, and marking a property
            # that does not exist as required would make the form unusable
            # rather than say so.
            if name in properties and name not in required:
                required.append(name)
        schema["required"] = required
        self._offer_addresses(properties)
        return schema

    def _offer_addresses(self, properties: dict) -> None:
        """Put the offered addresses into the ``emails`` field's schema.

        Only while the question is open. Once the profile carries an address
        the person has answered, and turning their own field into a list of
        somebody else's suggestions would be a worse form than the plain box.

        The decoration goes on ``items`` rather than on the field, because
        ``emails`` is an array and its entries are what a widget renders a
        choice for. ``enum``/``enumNames``/``choices`` is the trio
        ``plone.restapi`` emits for a ``Choice``, so a widget that renders
        one of those renders this without being taught anything new.

        :param properties: The schema's properties, edited in place.
        """
        field = properties.get("emails")
        if not isinstance(field, dict):
            return
        items = field.get("items")
        if not isinstance(items, dict):
            return
        userid = api.user.get_current().getId()
        if not userid or self._has_address(userid):
            return
        offered = offered_addresses(userid)
        if not offered:
            return
        addresses = [choice["address"] for choice in offered]
        items["enum"] = addresses
        items["enumNames"] = [self._label(choice) for choice in offered]
        items["choices"] = [
            [choice["address"], self._label(choice)] for choice in offered
        ]

    @staticmethod
    def _label(choice: dict) -> str:
        """Describe one offered address to the person choosing.

        Named by the provider that offered it, because somebody with two
        linked accounts is being shown two lists merged into one and the
        address alone does not say which is which.

        :param choice: One entry from
            :func:`~pas.plugins.identity.core.emailchoices.offered_addresses`.
        :returns: The label.
        """
        provider = choice.get("provider") or ""
        return f"{choice['address']} ({provider})" if provider else choice["address"]

    @staticmethod
    def _has_address(userid: str) -> bool:
        """Report whether this user's profile already carries an address.

        Off the catalog brain, like everything else that asks a question about
        a profile on a request that is not about the profile.

        :param userid: The current user's id.
        :returns: Whether an address is already recorded.
        """
        from pas.plugins.identity.core.catalog import query_catalog

        catalog = query_catalog()
        if catalog is None:
            return False
        brains = catalog.unrestrictedSearchResults(userid=userid)
        return bool(brains and (getattr(brains[0], "emails", None) or ()))


__all__ = ["ProfileTypesGet", "user_content_type"]
