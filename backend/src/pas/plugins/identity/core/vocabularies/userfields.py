"""The user fields a provider claim can be mapped onto.

The source is the site's *live* member schema, not a fixed list:
:func:`~plone.app.users.browser.schemaeditor.getFromBaseSchema` merges
:class:`~plone.app.users.schema.IUserDataSchema` with the schema edited
through the web, so a site that added ``department`` in the **User Schema**
control panel can map a claim onto it without this package knowing about it.

``plone.app.users`` already ships ``plone.app.users.user_registration_fields``,
but that one is built from ``ICombinedRegisterSchema`` and therefore includes
``password``, ``password_ctl`` and ``mail_me`` -- registration mechanics
rather than profile fields, and nothing a provider claim should ever be
written to.
"""

from plone.app.users.browser.schemaeditor import getFromBaseSchema
from plone.app.users.schema import IUserDataSchema
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
USER_FIELDS_VOCABULARY = "pas.plugins.identity.UserFields"


@implementer(IVocabularyFactory)
class UserFieldsVocabulary:
    """List the member fields a claim may be written to."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from the site's member schema.

        :param context: The context the vocabulary is looked up on. Unused:
            the member schema is site-wide.
        :returns: One term per field, titled with the field's own label so
            the control panel reads the way the user-information form does.
        """
        schema = getFromBaseSchema(IUserDataSchema)
        terms = [
            SimpleTerm(value=name, token=name, title=schema[name].title or name)
            for name in schema
        ]
        terms.sort(key=lambda term: term.title.lower())
        return SimpleVocabulary(terms)


UserFieldsVocabularyFactory = UserFieldsVocabulary()
