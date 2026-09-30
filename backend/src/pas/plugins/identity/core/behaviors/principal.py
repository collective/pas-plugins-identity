"""Behaviors that make a site's own content type a user or a group.

A site that keeps its users as a type of its own -- a ``Person`` -- names it in
``pas.plugins.identity.user_content_type``, and the type then has to be two
things at once: a user, which
:class:`~pas.plugins.identity.core.interfaces.IUserContent` says, so the
adder will create it; and a Profile, which
:class:`~pas.plugins.identity.core.interfaces.IUserProfile` says, so the
identity catalog files it and the Profile plugin enumerates it. Groups are the
same pair, :class:`~pas.plugins.identity.core.interfaces.IGroupContent` and
:class:`~pas.plugins.identity.core.interfaces.IUserGroup`. Enabling one
behavior gives a type both.

**Why a factory, for a behavior with nothing to adapt.** The obvious spelling
is a single interface extending both markers, registered as the behavior's
``provides``. It breaks other behaviors' fields in a way that is hard to
trace. ``IUserContent`` declares ``userid`` and ``login`` as ``Attribute``
objects, and ``IGroupContent`` declares ``group_id``. Dexterity answers a
missing attribute by walking each enabled behavior's ``provides`` interface
and reading ``.default`` off the first thing it finds under that name. Found
first, the ``Attribute`` -- which has no ``default`` -- ends the lookup with an
``AttributeError``, and a real ``login`` field a later behavior supplies is
never reached: its default is never answered.

So ``provides`` is an interface that declares nothing, which Dexterity has no
reason to read, and the two markers arrive as the behavior's ``marker``.
``plone.behavior`` accepts a separate marker only alongside a factory, and the
factories here adapt nothing because there is nothing to adapt.
"""

from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.interfaces import IUserGroup
from pas.plugins.identity.core.interfaces import IUserProfile
from zope.interface import implementer
from zope.interface import Interface


class IPrincipalUser(IUserContent, IUserProfile):
    """Marker applied by ``pas.plugins.identity.principal_user``.

    A user the adder may create, and a Profile the identity catalog files.
    """


class IPrincipalGroup(IGroupContent, IUserGroup):
    """Marker applied by ``pas.plugins.identity.principal_group``.

    A group the group manager may create, and one the identity catalog files.
    """


class IPrincipalUserBehavior(Interface):
    """What ``pas.plugins.identity.principal_user`` provides: nothing.

    Deliberately empty; see the module docstring.
    """


class IPrincipalGroupBehavior(Interface):
    """What ``pas.plugins.identity.principal_group`` provides: nothing.

    Deliberately empty; see the module docstring.
    """


@implementer(IPrincipalUserBehavior)
class PrincipalUser:
    """Factory for ``pas.plugins.identity.principal_user``."""

    def __init__(self, context) -> None:
        """Bind the adapter to the object.

        :param context: The content object.
        """
        self.context = context


@implementer(IPrincipalGroupBehavior)
class PrincipalGroup:
    """Factory for ``pas.plugins.identity.principal_group``."""

    def __init__(self, context) -> None:
        """Bind the adapter to the object.

        :param context: The content object.
        """
        self.context = context


__all__ = [
    "IPrincipalGroup",
    "IPrincipalGroupBehavior",
    "IPrincipalUser",
    "IPrincipalUserBehavior",
    "PrincipalGroup",
    "PrincipalUser",
]
