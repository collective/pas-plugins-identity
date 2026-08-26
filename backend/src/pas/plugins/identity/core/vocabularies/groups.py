"""The groups a principal can be put in.

Membership is stored as ids on the member, which for as long as the field was
a free-text tuple meant a typo created a membership in a group that does not
exist -- silently, because the groups plugin filters an unknown id out rather
than complaining. A vocabulary turns that into something a form can refuse.

Every group PAS knows, not only the ones that are content: a site may keep
some principals in ``source_groups`` and some as content, and membership
names an id without caring which plugin answers for it.
"""

from plone import api
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
GROUPS_VOCABULARY = "pas.plugins.identity.Groups"

#: Groups nobody is explicitly a member of, so offering them would be a way
#: to store a membership that means nothing. ``AuthenticatedUsers`` is
#: computed from being logged in.
VIRTUAL_GROUPS = frozenset({"AuthenticatedUsers"})


@implementer(IVocabularyFactory)
class GroupsVocabulary:
    """List the groups a principal may belong to."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from the site's groups.

        :param context: The context the vocabulary is looked up on. Unused:
            groups are site-wide.
        :returns: One term per real group, titled the way a group listing
            titles it, ordered by that title.
        """
        terms = []
        for group in api.group.get_groups():
            group_id = group.getId()
            if group_id in VIRTUAL_GROUPS:
                continue
            title = group.getProperty("title", "") or group_id
            terms.append(SimpleTerm(value=group_id, token=group_id, title=title))
        terms.sort(key=lambda term: term.title.lower())
        return SimpleVocabulary(terms)


GroupsVocabularyFactory = GroupsVocabulary()
