"""The ``PrincipalsContainer`` content type.

The folder Profiles and groups are filed in. This package creates one at the
path the registry names, the first time something needs it -- see
:func:`~pas.plugins.identity.core.container.get_container` -- and an
administrator may add more wherever they choose.

It replaced a plain ``Folder``, which was the wrong fit in three ways. Each of
them is now a property of this type:

**Unordered.** A ``Folder`` keeps an explicit position for every item it
holds, rewritten on every add and every delete. For a list of people that
order means nothing, and its cost grows with the site's user base.
``plone.folder`` chooses the ordering policy by the name of an adapter, so
this class names the ``unordered`` one.

**Blocks.** The FTI enables ``volto.blocks``, so the folder's page can be
edited like any other page: an introduction, a listing of the people in it.

**Its own add permission.** Adding a ``Folder`` is something every
Contributor may do, and deciding where principals are filed is not an
authoring decision. The FTI names
``pas.plugins.identity.principalscontainer.add``, which ``rolemap.xml``
grants to Manager and Site Administrator.

The class is stored under its dotted name in every site that has a container,
so moving it is a data migration rather than a refactor.
"""

from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class IPrincipalsContainerSchema(model.Schema):
    """Schema of the PrincipalsContainer content type.

    Empty on purpose. The title, the description, exclusion from navigation
    and the blocks all come from behaviors the FTI enables, and a field
    declared here as well would be the same field twice.
    """


@implementer(IPrincipalsContainerSchema)
class PrincipalsContainer(Container):
    """A folder of principals, keeping no order among them."""

    #: The ``plone.folder`` ordering adapter, by name. Declared on the class
    #: rather than set on each object after it is created, so that a container
    #: made any other way -- through the add form, by an import -- is
    #: unordered too.
    _ordering = "unordered"
