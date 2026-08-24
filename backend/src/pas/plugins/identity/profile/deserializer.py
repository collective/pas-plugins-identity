"""Refuse a ``userid`` change over the REST API.

The field is permanent: an identity record, every local role granted on the
Profile and the catalog entry the enumeration plugin queries all point at it,
and rewriting it detaches all three at once while leaving a Profile that
still looks correct.

The edit form renders it read-only, which covers a person with a browser. A
PATCH is not a form. Refusing it in the deserializer rather than on the
object is deliberate: ``plone.restapi`` collects what a deserializer raises
into a 400 naming the field, while an exception from the assignment itself
escapes as a 500 -- the same refusal, reported as a bug in the site.
"""

from pas.plugins.identity import _
from pas.plugins.identity.profile.content.profile import IProfileSchema
from plone.restapi.deserializer.dxfields import DefaultFieldDeserializer
from plone.restapi.interfaces import IFieldDeserializer
from typing import Any
from zope.component import adapter
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.interfaces import ITextLine
from zope.schema.interfaces import ValidationError


class UseridIsPermanent(ValidationError):
    """A Profile's ``userid`` was rewritten."""

    __doc__ = _(
        "The user id is permanent. It is what an identity, a local role "
        "and the catalog entry for this Profile all point at, so changing "
        "it would detach every one of them."
    )


@implementer(IFieldDeserializer)
@adapter(ITextLine, IProfileSchema, IBrowserRequest)
class ProfileTextLineDeserializer(DefaultFieldDeserializer):
    """The default deserializer, plus one field that may not change.

    Registered for every text line on a Profile rather than for ``userid``
    alone, because a deserializer is looked up by field *type*: there is no
    narrower registration to make. Every other field is handed straight to
    the default, so this adds one comparison and no behaviour.
    """

    def __call__(self, value: Any) -> Any:
        """Deserialize the value, refusing a changed ``userid``.

        :param value: The submitted value.
        :returns: The deserialized value.
        :raises UseridIsPermanent: When it would change an existing userid.
        """
        deserialized = super().__call__(value)
        if self.field.__name__ != "userid":
            return deserialized
        current = getattr(self.context, "userid", None)
        # Only a *change*. A PATCH that echoes the value back is what a form
        # round-trip does, and refusing it would make the field impossible to
        # send rather than impossible to alter.
        if current and deserialized != current:
            raise UseridIsPermanent(deserialized)
        return deserialized
