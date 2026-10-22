"""A behavior a site adds to its user type, for the tests that need one."""

from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from zope import schema
from zope.annotation.interfaces import IAnnotations
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


#: Name the behavior in :class:`IExtraProfileFields` is registered under.
EXTRA_BEHAVIOR = "pas.plugins.identity.tests.extra_profile_fields"


@provider(IFormFieldProvider)
class IExtraProfileFields(model.Schema):
    """A behavior a site adds to its user type.

    ``social_links`` has the shape ``plonegovbr.socialmedia.links`` gives its
    field: a list of mappings, which is what a provider that is another Plone
    site releases as a claim.
    """

    social_links = schema.List(
        title="Social links",
        value_type=schema.Dict(key_type=schema.TextLine()),
        required=False,
    )
    tags = schema.Tuple(title="Tags", value_type=schema.TextLine(), required=False)
    age = schema.Int(title="Age", required=False)
    badge = schema.TextLine(title="Badge", readonly=True, required=False)


#: Name the behavior in :class:`IAnnotatedProfileFields` is registered under.
ANNOTATED_BEHAVIOR = "pas.plugins.identity.tests.annotated_profile_fields"

#: Annotation key :class:`AnnotatedProfileFields` stores under.
ANNOTATION_KEY = "pas.plugins.identity.tests.nickname"


@provider(IFormFieldProvider)
class IAnnotatedProfileFields(model.Schema):
    """A behavior whose factory stores somewhere other than the object."""

    nickname = schema.TextLine(title="Nickname", required=False)


@implementer(IAnnotatedProfileFields)
@adapter(IDexterityContent)
class AnnotatedProfileFields:
    """Keep ``nickname`` in an annotation, as a factory behavior may."""

    def __init__(self, context) -> None:
        self.context = context

    @property
    def nickname(self) -> str | None:
        """Return the stored nickname.

        :returns: The value, or ``None``.
        """
        return IAnnotations(self.context).get(ANNOTATION_KEY)

    @nickname.setter
    def nickname(self, value: str | None) -> None:
        """Store the nickname.

        :param value: The value.
        """
        IAnnotations(self.context)[ANNOTATION_KEY] = value
