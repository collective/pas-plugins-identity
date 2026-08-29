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

This service used to do a second job: decorate the ``emails`` field with the
addresses a provider had offered but nobody had picked between, so the form
rendered a choice rather than an empty box. Nothing offers them any more --
every address a provider reports goes straight onto the Profile, so the field
this would have decorated is never empty when there is anything to put in it.
See :func:`~pas.plugins.identity.core.subscribers.sync_addresses`.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.completeness import configured_fields
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
        return schema


__all__ = ["ProfileTypesGet", "user_content_type"]
