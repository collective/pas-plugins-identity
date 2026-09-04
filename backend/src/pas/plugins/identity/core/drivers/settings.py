"""What an operator configures for a provider, as schemas rather than dicts.

Every field below used to be an entry in a hand-built ``JSONDict`` returned by
``BaseDriver.config_schema()`` -- ``{"type": "string", "title": "Client ID",
"required": True, "secret": False, "order": 20}`` -- and the frontend turned
that into a form schema in 529 lines of TypeScript. It was wrong in four ways
at once and Érico called it (2026-08-29):

* **No translation.** Every title and description was an untranslated Python
  literal, so a driver's fields were English on every site in the world while
  the rest of the package went through ``_()`` and the ``.po`` files.
* **No Classic UI.** A form can only be built from that dict by whoever
  reimplements the dict, which meant Volto and nothing else. A schema builds
  a z3c.form as readily as a JSON one.
* **No validation.** ``required`` was a hint to a form; nothing refused a
  ``POST`` that omitted a required field or put a string in an int.
* **Everything reinvented, worse.** ``order`` spaced by tens exists only
  because a JSON object loses ordering, which ``zope.schema`` has
  intrinsically; ``secret`` duplicates :class:`~zope.schema.Password`;
  ``choices`` as pairs is a vocabulary; ``type`` is a field class.

So a driver names an ``Interface`` and ``@identity-drivers`` serializes it
with ``plone.restapi``'s own machinery -- the same call chain that answers
``@controlpanels``. What the frontend receives is an ordinary JSON schema with
``properties``, ``required``, ``fieldsets`` and ``widget``; what it has to
know about this package is nothing.

**Defaults are not here.** Which scope GitHub needs and which userid source
suits a peer are facts about a *driver*, and they stay on the driver class as
``default_scope`` and friends. Putting them on the field instead would mean a
subinterface redeclaring a field to change its default, and a redeclared field
takes a fresh creation order -- so the price of a different default would be a
field that silently jumps to the end of the form. The schema describes shape,
labels and widgets; the driver says what a new provider starts with.
"""

from pas.plugins.identity import _
from plone.autoform import directives
from zope import schema
from zope.interface import Interface
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Where a Plone userid is minted from on a first sign-in.
#:
#: A vocabulary rather than the ``choices`` list-of-pairs the hand-built
#: schema carried, so the terms are translated once here and every form --
#: Volto's select, a z3c.form radio group, a ``@vocabularies`` lookup -- reads
#: the same source.
#: Terms are built positionally as ``(value, token, title)``: the keyword form
#: trips ruff's hardcoded-password check on ``token=``, which is a false
#: positive it has no way to tell from a real one.
USERID_SOURCES = SimpleVocabulary([
    SimpleTerm("uuid", "uuid", _("A random id")),
    SimpleTerm("username", "username", _("The provider's username")),
    SimpleTerm("email", "email", _("The email address")),
    SimpleTerm("subject", "subject", _("The provider's subject identifier")),
])


class IDriverSettings(Interface):
    """Base for every driver's configuration schema.

    Carries no fields. It exists so that a driver's ``settings_schema`` can be
    type-checked against something, and so an integrator writing a driver has
    an obvious thing to extend.
    """


class IOAuth2Settings(IDriverSettings):
    """What every OAuth2 and OIDC provider needs.

    Declared in the order an operator fills them in, which is the order the
    form renders: the credentials first, then what to do with the account they
    identify.
    """

    client_id = schema.TextLine(
        title=_("Client ID"),
        description=_("The identifier this provider issued for this site."),
        required=True,
    )

    client_secret = schema.Password(
        title=_("Client secret"),
        description=_(
            "Write-only. It is never sent back by any endpoint here, and a "
            "GenericSetup export carries a placeholder rather than the value."
        ),
        required=True,
    )

    scope = schema.Tuple(
        title=_("Scope"),
        description=_(
            "One permission per entry. They are joined with spaces when the "
            "authorize URL is built, which is the encoding OAuth 2 defines -- "
            "a scope containing a space is not one scope."
        ),
        value_type=schema.TextLine(),
        required=False,
        missing_value=(),
        default=(),
    )
    directives.widget("scope", frontendOptions={"widget": "token"})

    userid_source = schema.Choice(
        title=_("Userid taken from"),
        description=_(
            "What the Plone userid is minted from the first time somebody "
            "signs in with this provider. A random id is the safe default: it "
            "leaks nothing and never has to change. The others are readable, "
            "which matters when a person has to be recognised in Plone -- and "
            "they are claims, so two providers can offer the same one. A "
            "userid already in use is never handed out: the new one gets a "
            "numeric suffix."
        ),
        vocabulary=USERID_SOURCES,
        required=False,
        default="uuid",
    )

    trust_email_verification = schema.Bool(
        title=_("This provider's email verification counts"),
        description=_(
            "When this provider says it verified an address, record the "
            "address as verified here too -- exactly as a magic link from "
            "this site would. Switch it on only for a provider that really "
            "does check, since a verified address is what an account can be "
            "attached to. Anything left off still shows what the provider "
            "claimed; it just proves nothing."
        ),
        required=False,
        default=False,
    )

    accept_string_booleans = schema.Bool(
        title=_("This provider sends verification flags as text"),
        description=_(
            'Some providers send email_verified as the string "true" rather '
            "than as a boolean -- Oracle Access Manager does, and so do some "
            "Keycloak configurations. Only a real boolean counts here, so "
            "against such a provider every address arrives unverified and "
            "nothing explains why. Switch this on for that provider only, "
            "having established that this is what it does: it repairs the "
            "value before anything reads it, and changes nothing about what "
            "a verified address then means."
        ),
        required=False,
        default=False,
    )

    auto_link_by_email = schema.Bool(
        title=_("Attach to an existing account with the same verified email"),
        description=_(
            "Matches a verified address: one this site confirmed with a magic "
            "link, or one a provider it trusts confirmed. Needs this "
            "provider's own verification to be trusted too, since the address "
            "being matched on is the one it just sent."
        ),
        required=False,
        default=False,
    )


class IOIDCSettings(IOAuth2Settings):
    """A provider reachable through OpenID Connect discovery."""

    issuer = schema.TextLine(
        title=_("Issuer URL"),
        description=_(
            "Discovery is fetched from <issuer>/.well-known/openid-configuration."
        ),
        required=True,
    )
    # Ahead of the credentials: everything else about this provider is read
    # from what the issuer discovers, so it is the first thing to fill in.
    directives.order_before(issuer="client_id")

    group_claim = schema.TextLine(
        title=_("Groups arrive in the claim"),
        description=_(
            "Which claim carries the group names this provider asserts. A "
            "dotted path reaches into a nested claim, so a provider putting "
            "them under realm_access.roles is reachable without a driver of "
            "its own. What the names then grant is the group map, which is "
            "empty until an operator fills it in -- an unmapped group grants "
            "nothing and is never created here."
        ),
        required=False,
        default="",
    )

    picture_over_http = schema.Bool(
        title=_("Allow the avatar to be fetched over plain HTTP"),
        description=_(
            "Only for a provider on a network you control -- a demo or "
            "development stack with no certificate. Portrait syncing fetches "
            "a URL the provider supplies, and over plain HTTP that fetch can "
            "be aimed at an internal service and read back through the "
            "portrait. Leave this off for any provider on the public internet."
        ),
        required=False,
        default=False,
    )


class IGitHubSettings(IOAuth2Settings):
    """GitHub needs nothing an OAuth2 provider does not.

    Its own particulars -- the address endpoint, the numeric subject, the
    login as a userid -- are facts about the driver rather than settings an
    operator types, so none of them appears here.
    """


class IPloneIdentitySettings(IOIDCSettings):
    """A peer running this same package's ``[server]`` layer.

    Identical to any other OIDC provider except for what an operator has to be
    told about the issuer: for a Plone site it is the site root, and the
    trailing path segment people reach for is what makes discovery 404.
    """

    issuer = schema.TextLine(
        title=_("Issuer URL"),
        description=_(
            "The other site's URL, as it serves "
            "/.well-known/openid-configuration -- for a Plone site that is "
            "the site root, with no path segment after it."
        ),
        required=True,
    )
    # Redeclaring a field gives it a fresh creation order, so the position has
    # to be restated as well as the wording.
    directives.order_before(issuer="client_id")


class IEmailSettings(IDriverSettings):
    """Magic-link sign-in, which has no OAuth client to configure.

    The "provider" is a mailbox, so none of the OAuth2 fields apply and this
    does not extend them. The signing key lives with the plugin rather than in
    the registry, which is why there is no secret here either.
    """

    token_ttl = schema.Int(
        title=_("Link lifetime (seconds)"),
        description=_(
            "How long a link stays redeemable. Capped at fifteen minutes "
            "whatever is configured, and a token is burned after one use."
        ),
        required=False,
        default=900,
    )

    rate_limit_per_hour = schema.Int(
        title=_("Links per address per hour"),
        description=_(
            "Also applied per requesting address. The endpoint answers "
            "identically whether or not the address belongs to an account, so "
            "this is what stops it being used to enumerate them."
        ),
        required=False,
        default=5,
    )


__all__ = [
    "USERID_SOURCES",
    "IDriverSettings",
    "IEmailSettings",
    "IGitHubSettings",
    "IOAuth2Settings",
    "IOIDCSettings",
    "IPloneIdentitySettings",
]
