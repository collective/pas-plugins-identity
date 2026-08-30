"""Serializing an ``Interface`` the way ``plone.restapi`` serializes anything.

One function, and it exists so there is one spelling of it. Two endpoints
answer with a form schema -- ``@identity-drivers`` for a provider's driver
settings and ``@identity-clients`` for an OAuth client -- and a second
composition of these calls would eventually disagree with the first about
fieldsets, required fields or widgets.

The composition is ``plone.restapi``'s own, lifted from
``get_jsonschema_for_controlpanel``: build the fieldsets through
``plone.autoform`` so ``order_before``, widget directives and fieldset
declarations are honoured, then read the properties, the required names and
the fieldset descriptions off them. Nothing here knows anything about this
package.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from plone.restapi.types import utils


def jsonschema_for(schema, context, request) -> JSONDict:
    """Render an interface as a JSON schema.

    :param schema: The ``Interface`` to serialize.
    :param context: Context to build the form against.
    :param request: The current request, which decides the language every
        title and description is translated into.
    :returns: A JSON schema with ``properties``, ``required`` and
        ``fieldsets``.
    """
    fieldsets = utils.get_fieldsets(context, request, schema)
    return {
        "type": "object",
        "properties": utils.get_jsonschema_properties(context, request, fieldsets),
        "required": [
            field.field.getName()
            for field in utils.iter_fields(fieldsets)
            if field.field.required
        ],
        "fieldsets": utils.get_fieldset_infos(fieldsets),
    }


__all__ = ["jsonschema_for"]
