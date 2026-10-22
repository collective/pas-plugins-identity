"""The Profile fields a provider claim can be mapped onto.

:func:`~pas.plugins.identity.core.utils.propertymap.mappable_fields` is the
source, and the reasons a field is left out are written against
:data:`~pas.plugins.identity.core.utils.propertymap.UNMAPPABLE_FIELDS`. This
module is the part an operator sees: one term per field, titled with the
field's own label so the control panel reads the way the profile form does.

**The site's user type, not its member schema.** This was once built from
:func:`~plone.app.users.browser.schemaeditor.getFromBaseSchema` over
:class:`~plone.app.users.schema.IUserDataSchema`, on the premise that a site
adding ``department`` in the **User Schema** control panel could then map a
claim onto it. That premise does not hold here: a Profile is content, and a
site adds a field to it with a behavior. So the terms are the fields of the
configured user type and every behavior it enables, read when the vocabulary
is asked for -- a behavior enabled a moment ago is a choice now.
"""

from pas.plugins.identity.core.utils.propertymap import mappable_fields
from zope.i18n import translate
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
USER_FIELDS_VOCABULARY = "pas.plugins.identity.UserFields"


@implementer(IVocabularyFactory)
class UserFieldsVocabulary:
    """List the Profile fields a claim may be written to."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from the fields a map may write.

        :param context: The context the vocabulary is looked up on. Unused:
            which fields a map may write is a property of the site's user
            type, not of the object a form is being built against -- and the
            registry validates a record with no context at all.
        :returns: One term per mappable field, in schema order. A field with
            no title is titled with its name.
        """
        return SimpleVocabulary([
            SimpleTerm(value=name, token=name, title=translate(field.title or name))
            for name, field in mappable_fields().items()
        ])


UserFieldsVocabularyFactory = UserFieldsVocabulary()
