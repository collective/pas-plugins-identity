"""Whether a profile carries the information the site requires of it.

A provider is not obliged to tell us anything. GitHub will withhold an email
address the user has marked private, a bare OIDC provider may release nothing
beyond ``sub``, and a magic link knows only the address it was sent to. So a
profile minted at first login is routinely missing something the site needs,
and the site has to be able to insist.

**The workflow state is the answer, not a second store.** ``incomplete`` means
"missing something required" and ``complete`` means "not missing anything".
That was already what the two states were called; what was missing is anything
keeping them true. Nothing ever fired ``complete``, so every profile stayed
``incomplete`` for ever and the frontend's first-login routing diverted every
user on every login.

Keeping the state true rather than adding a "profile is complete" flag is what
lets everything downstream stay as it is: the catalog already carries
``review_state`` as metadata, so ``@my-profile`` still answers from a brain
and the enumeration plugin still filters on states from the registry.

:func:`reconcile` runs on every login and on every write to a profile. Both,
because either alone leaves an obvious hole: only-on-login means a user who
has just filled the form in is still told it is incomplete until they log in
again, and only-on-write means a profile whose provider stopped sending a
claim is never re-examined.

``deactivated`` is never touched by any of this. That state is an
administrator's decision about an account, and a machine that reads "not
missing anything" has no business reversing it.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.content.container import PREFIX
from pas.plugins.identity.content.profile import IUserProfileSchema
from pas.plugins.identity.content.profile import UserProfile
from plone import api
from plone.api.exc import InvalidParameterError
from plone.dexterity.utils import iterSchemata
from zope.schema import getFieldsInOrder


#: Registry record naming the fields a profile must carry. Empty means "the
#: ones the type marks required", which is what :func:`required_fields`
#: falls back to.
REQUIRED_FIELDS_RECORD = f"{PREFIX}.required_profile_fields"

#: The state a profile is in while it is missing something.
INCOMPLETE = "incomplete"

#: The state a profile is in once it is not.
COMPLETE = "complete"

#: Transition to fire in each direction, keyed by the state to leave.
TRANSITIONS = {INCOMPLETE: "complete", COMPLETE: "reopen"}

#: Fields never counted, whatever the schema says about them. ``userid`` is
#: computed from the object's id and can never be empty; asking a user to
#: supply it would be asking them to supply the thing that identifies the
#: form they are filling in.
NEVER_REQUIRED = frozenset({"userid", "id"})


def configured_fields() -> tuple[str, ...]:
    """Return the fields the registry names, if any.

    Public because the ``@types`` service needs the same answer without a
    profile object to hand: it is correcting a *type's* schema, and the
    fields the type already marks required are in that schema already.

    :returns: Field names, empty when the record is unset or absent.
    """
    try:
        value = api.portal.get_registry_record(REQUIRED_FIELDS_RECORD, default=())
    except InvalidParameterError:
        # A site without this layer's settings. Nothing requires anything.
        return ()
    return tuple(name for name in (value or ()) if name)


def _declared(profile: UserProfile) -> tuple[str, ...]:
    """Return the fields the profile's own type marks required.

    Read from the object rather than from
    :class:`~pas.plugins.identity.content.profile.IUserProfileSchema`, and
    through ``iterSchemata`` rather than the FTI's own schema, so that a site
    running its own user type or a behavior that adds a required field gets
    the answer for the type it actually has.

    :param profile: The profile to inspect.
    :returns: Field names, in schema order.
    """
    names = []
    for schema in iterSchemata(profile):
        for name, field in getFieldsInOrder(schema):
            if field.required and name not in NEVER_REQUIRED and name not in names:
                names.append(name)
    return tuple(names)


def required_fields(profile: UserProfile) -> tuple[str, ...]:
    """Return the fields this profile must carry to count as complete.

    :param profile: The profile to inspect.
    :returns: Field names.
    """
    return configured_fields() or _declared(profile)


def _is_empty(value: object) -> bool:
    """Return whether a field value counts as not filled in.

    ``0`` and ``False`` are values somebody supplied and are not missing;
    ``None``, the empty string and an empty collection are. Written out rather
    than left to ``bool`` because a required numeric field holding zero is
    exactly the case a truthiness test gets wrong.

    :param value: The stored value.
    :returns: Whether it counts as missing.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return not value
    return False


def missing_fields(profile: UserProfile) -> tuple[str, ...]:
    """Return the required fields this profile has no value for.

    :param profile: The profile to inspect.
    :returns: Field names, in the order :func:`required_fields` gives them.
    """
    return tuple(
        name
        for name in required_fields(profile)
        if _is_empty(getattr(profile, name, None))
    )


def missing_from_brain(brain) -> tuple[str, ...]:
    """Return the required fields a catalog brain shows no value for.

    The same question as :func:`missing_fields`, asked of a brain so that the
    caller does not have to wake the object. ``@my-profile`` is answered on
    every page load by the frontend gate, and this package's whole claim about
    the catalog is that reading a user costs no object load.

    Every field of the shipped type except the picture is catalog metadata, so
    in practice this answers completely. A configured field that is *not* a
    metadata column cannot be judged from a brain and is reported as missing:
    the workflow state is the authority on whether anything is missing at all,
    and this list only explains it. Saying too much is a worse-worded prompt;
    saying too little is a prompt that names nothing.

    :param brain: A brain from the identity catalog.
    :returns: Field names.
    """
    names = configured_fields() or _brain_declared()
    return tuple(name for name in names if _is_empty(getattr(brain, name, None)))


def _brain_declared() -> tuple[str, ...]:
    """Return the required fields of the shipped type, without an object.

    :func:`_declared` reads them off the object through ``iterSchemata``,
    which is right when there is one. There is not here, and the FTI's own
    schema is the closest honest answer.

    :returns: Field names, in schema order.
    """
    names = []
    for name, field in getFieldsInOrder(IUserProfileSchema):
        if field.required and name not in NEVER_REQUIRED:
            names.append(name)
    return tuple(names)


def is_complete(profile: UserProfile) -> bool:
    """Return whether a profile carries everything the site requires.

    :param profile: The profile to inspect.
    :returns: Whether nothing is missing.
    """
    return not missing_fields(profile)


def reconcile(profile: UserProfile) -> str | None:
    """Bring a profile's workflow state in line with what it carries.

    Fires ``complete`` when nothing is missing and ``reopen`` when something
    is, and does nothing at all in any other state -- which in practice means
    ``deactivated``, and means it deliberately.

    Runs elevated. The transitions are guarded by ``Modify portal content``,
    which the person this profile belongs to holds on their own profile, but
    the paths that call this are a login subscriber and a write subscriber and
    neither is reliably running as anybody in particular.

    :param profile: The profile to reconcile.
    :returns: The transition fired, or ``None`` when nothing was needed.
    """
    state = api.content.get_state(obj=profile, default=None)
    if state not in TRANSITIONS:
        return None

    wanted = COMPLETE if is_complete(profile) else INCOMPLETE
    if state == wanted:
        return None

    transition = TRANSITIONS[state]
    with api.env.adopt_roles(["Manager"]):
        api.content.transition(obj=profile, transition=transition)
    logger.info(
        "Profile %s: %s (missing %s)",
        getattr(profile, "userid", "?"),
        transition,
        ", ".join(missing_fields(profile)) or "nothing",
    )
    return transition


__all__ = [
    "COMPLETE",
    "INCOMPLETE",
    "REQUIRED_FIELDS_RECORD",
    "configured_fields",
    "is_complete",
    "missing_fields",
    "missing_from_brain",
    "reconcile",
    "required_fields",
]
