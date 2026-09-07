"""A person's addresses, as a behavior.

``emails`` and ``email`` used to be fields on the Profile schema. Same fields,
same storage -- a schema-only behavior stores its attributes on the content
object, so a Profile still answers ``profile.emails`` and the catalog still
indexes ``email`` -- but they are now something a *type* opts into.

The move is what makes the pair reusable. A site running its own user type
gets the list, the derived value and the two permissions by enabling one
behavior, rather than by declaring both fields again and keeping the
``viewpii`` read permission in step by hand.

**A list, and one value derived from it.** A person has more than one address,
signs in with more than one of them, and which one is theirs *here* is a
question whose answer changes. So ``emails`` is what is stored and ``email``
is computed: the first verified address, or the first address at all. Two
stored values that must agree, with nothing making them agree, is the shape
this package already paid for once with a ``userid`` that could drift from its
object id.

An address counts as verified when this site holds an ``email`` identity for
it, which is what a magic link creates. See
:mod:`pas.plugins.identity.core.utils.emails`, which also says why linking one
reindexes the Profile.

**The fields are declared here and the behaviour is on the class.** Both are
properties on :class:`~pas.plugins.identity.core.contents.profile.UserProfile`:
``emails`` normalizes and de-duplicates on write, ``email`` derives on read and
moves an address to the front when something writes it. A schema-only behavior
writes through ``setattr``, so those properties are still what runs.

**Its own fieldset.** The addresses are the one part of a Profile with a
different read permission -- ``viewpii`` rather than ``view``, so that a site
can let members find each other without publishing everybody's address -- and
a tab of their own is where that difference is legible. The personal fields
stay together on the default tab; see
:mod:`pas.plugins.identity.core.behaviors.details`.

**And the fieldset only exists because of the last line of this module.**
Enabling a behavior on a type does not put its fields on a form: ``@types`` and
every autoform-built form ask for the behaviors marked ``IFormFieldProvider``
and skip the rest, silently.
"""

from pas.plugins.identity import _
from plone.autoform.directives import read_permission
from plone.autoform.directives import write_permission
from plone.autoform.interfaces import IFormFieldProvider
from plone.schema import Email
from plone.supermodel import model
from zope import schema
from zope.interface import alsoProvides


#: Name the fieldset is registered under, and the id a form renders it with.
FIELDSET = "email"


class IEmailAddresses(model.Schema):
    """The addresses a person is reached and recognised by."""

    model.fieldset(
        FIELDSET,
        label=_("Email"),
        fields=["emails", "email"],
    )

    emails = schema.Tuple(
        title=_("Email addresses"),
        description=_(
            "The addresses this person uses, most preferred first. At least "
            "one is required: a Profile exists to be the thing somebody is "
            "reached and recognised by. Adding an address here does not "
            "prove it -- verifying one sends a link to it, and only an "
            "address this site has verified can be used to sign in or to "
            "attach a new provider account to this one."
        ),
        value_type=Email(title=_("Email")),
        # ``required`` rather than ``min_length=1``: zope.schema validates a
        # field's default when the schema is defined, and a one-address
        # minimum with an empty default fails at import time. Required plus a
        # ``missing_value`` of ``()`` says the same thing -- an empty tuple is
        # missing, and a form insists on an entry.
        required=True,
        missing_value=(),
        default=(),
    )

    email = Email(
        title=_("Email"),
        description=_(
            "The address that stands for this person: the first verified one "
            "in the list above, or the first one at all when none is "
            "verified. Derived rather than typed, so there is no second "
            "value to disagree with the list."
        ),
        required=False,
        readonly=True,
    )

    write_permission(emails="pas.plugins.identity.content.edit")
    read_permission(
        emails="pas.plugins.identity.content.viewpii",
        email="pas.plugins.identity.content.viewpii",
    )


# What makes the fields appear on a form at all; see the module docstring.
# Applied here rather than as a `provides=` in ZCML because the marker belongs
# to the schema, and a schema that is a form field provider on one site and
# not on another is a difference nobody would think to look for.
alsoProvides(IEmailAddresses, IFormFieldProvider)


__all__ = ["FIELDSET", "IEmailAddresses"]
