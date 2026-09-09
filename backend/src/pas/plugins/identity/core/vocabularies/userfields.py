"""The Profile fields a provider claim can be mapped onto.

:data:`~pas.plugins.identity.core.utils.propertymap.MAPPABLE_FIELDS` is the
source, and the reasons a field is in it or out of it are written there. This
module is the part an operator sees: one term per field, titled with the
field's own label so the control panel reads the way the profile form does.

**Not the site's member schema, which is what this used to be.** It was built
from :func:`~plone.app.users.browser.schemaeditor.getFromBaseSchema` over
:class:`~plone.app.users.schema.IUserDataSchema`, on the premise that a site
adding ``department`` in the **User Schema** control panel could then map a
claim onto it. That premise does not hold here: a Profile is content, a site
adds a field to it with a behavior rather than through that panel, and a login
writes only the closed set above however the map is written. What the old
vocabulary offered was therefore three fields that do nothing -- ``email``,
``portrait`` and ``pdelete`` -- alongside the four that do.

The titles come from the schemas that declare the fields rather than from a
list here, so a field renamed on the profile form is renamed in this picker in
the same commit.
"""

from pas.plugins.identity.core.behaviors.details import IProfileDetails
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from pas.plugins.identity.core.utils.propertymap import MAPPABLE_FIELDS
from zope.i18n import translate
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
USER_FIELDS_VOCABULARY = "pas.plugins.identity.UserFields"

#: The schemas that declare the mappable fields, in the order they are read.
#:
#: Two, because the Profile's own schema carries ``fullname`` and
#: ``description`` while the rest are on the details behavior. A field found
#: in neither is titled with its own name rather than dropped: the tuple is
#: what a login honours, and a picker that quietly offered three of four would
#: be a worse answer than an ugly label.
SCHEMATA = (IUserProfileSchema, IProfileDetails)


def field_title(name: str) -> str:
    """Return the label the profile form gives one field.

    :param name: The field name.
    :returns: The field's title, or the name when no schema declares it.
    """
    for schema in SCHEMATA:
        field = schema.get(name)
        if field is not None and field.title:
            return field.title
    return name


@implementer(IVocabularyFactory)
class UserFieldsVocabulary:
    """List the Profile fields a claim may be written to."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from the fields a map may write.

        :param context: The context the vocabulary is looked up on. Unused:
            which fields a map may write is a property of this package, not of
            the object a form is being built against.
        :returns: One term per mappable field, in the order they are declared.
        """
        return SimpleVocabulary([
            SimpleTerm(value=name, token=name, title=translate(field_title(name)))
            for name in MAPPABLE_FIELDS
        ])


UserFieldsVocabularyFactory = UserFieldsVocabulary()
