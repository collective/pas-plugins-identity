"""What an operator registers for an OAuth client, as a schema.

``ClientConfig`` was a plain Python class with hand-rolled ``serialize`` and
``deserialize``, stored as one JSON string in a single registry record, and
the Volto add-on rebuilt its form in 274 lines of TypeScript. Every objection
to the driver schema applies here and one more besides: the *provider* layer
had already learned this lesson and said so in its own docstring --

    Every provider setting is its own registry record [...] so a GenericSetup
    export lists the real fields with the real types rather than one opaque
    blob of JSON, and the generic registry editor can reach any single value.

-- while the server layer next door kept the blob (Érico, 2026-08-29).

So a client is an interface, its records are interface-bound like a
provider's, and ``@identity-clients`` serializes the schema rather than
describing it a second time in another language.

**The validation here is not decoration.** ``POST @identity-clients`` used to
store ``redirect_uris`` exactly as it received them: no scheme check, no
rejection of fragments, no loopback rule. A ``javascript:`` URI registered
that way is handed to a browser redirect at the end of an authorization flow.
The constraints below are where that is refused, and they are on the field so
that every route in -- the endpoint, a GenericSetup profile, a test -- is held
to the same rule.
"""

from pas.plugins.identity import _
from pas.plugins.identity.server.interfaces import GRANT_TYPES
from pas.plugins.identity.server.interfaces import PUBLIC_AUTH_METHOD
from pas.plugins.identity.server.vocabularies.scopes import SCOPES_VOCABULARY
from plone.autoform import directives
from plone.supermodel import model
from urllib.parse import urlsplit
from zope import schema
from zope.interface import Interface
from zope.interface import Invalid
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Fieldset the redirect and grant settings are edited in.
FLOW_FIELDSET = "flow"

#: Addresses a plain-HTTP redirect URI may name.
#:
#: The exception the OAuth 2 Security BCP makes, and the only one: a native
#: app cannot get a certificate for a loopback listener, so ``http://127.0.0.1``
#: is how a desktop client completes a flow. Every other ``http:`` target puts
#: an authorization code on the wire in clear.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})

#: The reserved name space that is loopback by definition.
#:
#: RFC 6761 reserves ``localhost`` and everything under ``.localhost`` to the
#: loopback interface, which is why browsers treat them as a secure context
#: without a certificate. So ``http://id.localhost`` is a development host
#: name rather than a plain-HTTP hole -- and this package's own federation
#: demo is two of them.
LOOPBACK_SUFFIX = ".localhost"


def is_loopback(host: str | None) -> bool:
    """Report whether a host name can only mean this machine.

    :param host: The host from a parsed URI, or ``None``.
    :returns: Whether plain HTTP to it stays on the loopback interface.
    """
    name = (host or "").lower()
    return (
        name in LOOPBACK_HOSTS or name == "localhost" or name.endswith(LOOPBACK_SUFFIX)
    )


#: Schemes a redirect URI may use.
#:
#: ``https`` for anything on a network, and a private-use scheme -- anything
#: with a dot in it, ``com.example.app:/callback`` -- for a native client,
#: which is what RFC 8252 registers. What is *not* here is the point:
#: ``javascript:``, ``data:`` and ``vbscript:`` are all executable in a
#: browser, and a redirect target is somewhere a browser is sent.
SAFE_SCHEMES = frozenset({"https"})


#: Fewest labels a wildcard may be followed by.
#:
#: ``https://*.example.com`` leaves two, which is a name somebody registered.
#: ``https://*.com`` leaves one, which is a public suffix -- the wildcard
#: would then span every site on it. The check is deliberately crude: a real
#: public-suffix list is a moving target and a dependency, and this rule
#: catches the shape that makes the mistake catastrophic rather than merely
#: wide.
MIN_LABELS_UNDER_WILDCARD = 2


def split_host_port(netloc: str) -> tuple[str, str]:
    """Split a netloc without validating the port.

    :func:`urllib.parse.urlsplit`'s ``port`` raises when the port is not a
    number, and ``*`` is exactly the value this module has to inspect and
    report on rather than crash over.

    :param netloc: The authority component.
    :returns: ``(host, port)``, the port empty when there is none. The host
        keeps its brackets for an IPv6 literal.
    """
    if netloc.endswith("]") or ":" not in netloc:
        return netloc, ""
    host, _sep, port = netloc.rpartition(":")
    if host.endswith("]") or "]" not in netloc:
        return host, port
    return netloc, ""


def check_host_wildcard(netloc: str) -> None:
    """Refuse a host wildcard that is not the whole leftmost label.

    ``https://*.example.com/cb`` stands for one label, so it matches
    ``https://app.example.com/cb`` and not ``https://a.b.example.com/cb`` -- a
    wildcard that crossed dots would cover a name space nobody registered. It
    does not match the bare ``https://example.com/cb`` either: that is a
    different host, and one more entry registers it.

    :param netloc: The authority component, known to contain a ``*``.
    :raises Invalid: When the wildcard is anywhere but the leftmost label.
    """
    if "@" in netloc:
        raise Invalid(_("A redirect URI may not use a wildcard with a user name."))
    host, port = split_host_port(netloc)
    if "*" in port:
        raise Invalid(_("A redirect URI may not use a wildcard in its port."))
    host = host.lower()
    if not host.startswith("*."):
        raise Invalid(
            _(
                "A wildcard host must be the whole leftmost label,"
                " as in https://*.example.com/callback."
            )
        )
    rest = host[2:]
    if "*" in rest:
        raise Invalid(_("A redirect URI may use only one host wildcard."))
    labels = rest.split(".")
    if len(labels) < MIN_LABELS_UNDER_WILDCARD or not all(labels):
        raise Invalid(
            _(
                "A wildcard host needs a registered domain under it,"
                " as in https://*.example.com/callback."
            )
        )


def check_path_wildcard(path: str) -> None:
    """Refuse a path wildcard that is not the whole last segment.

    ``https://example.com/*`` stands for any path on that host, and for any
    query string with it. A ``*`` in the middle reads as a prefix match and is
    not one.

    :param path: The path component, known to contain a ``*``.
    :raises Invalid: When the wildcard is anywhere but the last segment.
    """
    if not path.endswith("/*"):
        raise Invalid(
            _(
                "A wildcard path must be the whole last segment,"
                " as in https://example.com/app/*."
            )
        )
    if "*" in path[:-2]:
        raise Invalid(_("A redirect URI may use only one path wildcard."))


def check_wildcards(parts) -> None:
    """Refuse a ``*`` anywhere it does not belong.

    Two positions are allowed, because two are what a site actually needs: the
    whole leftmost host label, and the whole last path segment. See
    :func:`check_host_wildcard` and :func:`check_path_wildcard` for what each
    one covers.

    Everywhere else it is refused, and the refusals are the point. A ``*`` in
    the query string, the user name or the port is not a widening anybody
    asked for; a ``*`` in the middle of a label -- ``https://a*.example.com``
    -- reads as a prefix match and is not one; and a wildcard directly under a
    public suffix would hand every site on it a valid redirect target.

    The scheme needs no check: :func:`urllib.parse.urlsplit` only recognises
    one matching ``[a-zA-Z][a-zA-Z0-9+.-]*``, so ``http*://x`` parses as a
    relative path and :func:`is_redirect_uri` has already refused it for
    having no scheme.

    :param parts: The result of :func:`urllib.parse.urlsplit`.
    :raises Invalid: When a ``*`` appears anywhere but the two allowed spots.
    """
    if "*" in parts.query:
        raise Invalid(_("A redirect URI may not use a wildcard in its query string."))
    if "*" in parts.netloc:
        check_host_wildcard(parts.netloc)
    if "*" in parts.path:
        check_path_wildcard(parts.path)


def redirect_uri_matches(pattern: str, uri: str) -> bool:
    """Whether a presented redirect URI is covered by a registered one.

    A pattern with no ``*`` is compared as a string and nothing else, which
    is what every previously registered client still gets. A pattern with one
    is taken apart, because the comparison is no longer about the text:

    * The scheme and the port must be equal. Neither is ever widened, so a
      registration cannot be downgraded to plain HTTP by a presented URI.
    * The host is equal, or -- for a ``*.`` pattern -- one further label under
      it, compared case-insensitively as host names are.
    * The path is equal, or beneath a ``/*`` pattern.
    * The query must be equal, *unless* the path carries the wildcard: a
      pattern that stands for any path on a host stands for any query with
      it, and requiring an empty one would make the wildcard useless.

    :param pattern: One registered redirect URI, possibly with a wildcard.
    :param uri: The redirect URI as presented in the request.
    :returns: Whether the request may be redirected there.
    """
    if "*" not in pattern:
        return pattern == uri
    if not uri:
        return False
    registered = urlsplit(pattern)
    presented = urlsplit(uri)

    if registered.scheme != presented.scheme:
        return False
    if split_host_port(registered.netloc)[1] != split_host_port(presented.netloc)[1]:
        return False

    wanted = split_host_port(registered.netloc)[0].lower()
    got = (presented.hostname or "").lower()
    if wanted.startswith("*."):
        suffix = wanted[2:]
        if not got.endswith(f".{suffix}"):
            return False
        label = got[: -(len(suffix) + 1)]
        # One label, and a real one. `a.b.example.com` is a name space nobody
        # registered, and the empty string is `.example.com`.
        if not label or "." in label:
            return False
    elif wanted != got:
        return False

    if registered.path.endswith("/*"):
        # The trailing slash stays in the prefix, so `/app/*` covers
        # `/app/anything` and not `/application`.
        return presented.path.startswith(registered.path[:-1])
    return registered.path == presented.path and registered.query == presented.query


def is_redirect_uri(value: str) -> bool:
    """Refuse a redirect URI this server will not send a browser to.

    Four rules, each of which has a way of going wrong that is invisible until
    an authorization flow ends somewhere it should not:

    * **Absolute, with a scheme and a target.** Redirect matching is exact
      string comparison, and a relative value can never match what a client
      sends.
    * **No fragment.** The Security BCP requires refusing one: the
      authorization response appends its own fragment, and a registered
      fragment silently changes what the browser receives.
    * **A safe scheme.** ``https``, a private-use scheme for a native app, or
      ``http`` on loopback. Never ``javascript:`` or ``data:``.
    * **A wildcard only where one is allowed.** ``*`` may stand for the whole
      leftmost host label, or for the last segment of the path, and nowhere
      else -- see :func:`is_wildcard_pattern` for what each one widens and
      what it deliberately does not.

    :param value: One redirect URI.
    :returns: True, or the constraint has raised.
    :raises Invalid: When the URI is not one this server will redirect to.
    """
    uri = (value or "").strip()
    if not uri:
        raise Invalid(_("A redirect URI cannot be empty."))
    parts = urlsplit(uri)
    if not parts.scheme:
        raise Invalid(_("A redirect URI must be absolute, with a scheme."))
    if parts.fragment or uri.endswith("#"):
        raise Invalid(_("A redirect URI may not carry a fragment."))
    if "*" in uri:
        check_wildcards(parts)
    scheme = parts.scheme.lower()
    if scheme in SAFE_SCHEMES:
        if not parts.netloc:
            raise Invalid(_("A redirect URI must name a host."))
        return True
    if scheme == "http":
        if is_loopback(parts.hostname):
            return True
        raise Invalid(
            _("Plain HTTP is only allowed for a loopback address, such as 127.0.0.1.")
        )
    if "." in scheme:
        # A private-use scheme, which is what RFC 8252 registers for a native
        # app: reverse-domain, and never something a browser executes.
        return True
    raise Invalid(
        _(
            "A redirect URI must use https, a loopback address, or a"
            " private-use scheme such as com.example.app:/callback."
        )
    )


#: The grants a client may be registered for.
#:
#: Built from :data:`~pas.plugins.identity.server.interfaces.GRANT_TYPES`, so
#: the form offers exactly what the token endpoint implements and exactly what
#: discovery advertises. A registration naming anything else used to be stored
#: and then refused much later, at the token endpoint, where it reads as a
#: client bug rather than as a registration mistake.
GRANTS = SimpleVocabulary([SimpleTerm(grant, grant, grant) for grant in GRANT_TYPES])


class IClientRecords(Interface):
    """The fields every registered OAuth client has.

    Registered once per client, under
    ``pas.plugins.identity.clients.<id>`` as the prefix, exactly as a provider
    is -- so a GenericSetup export lists the real fields with the real types
    and a profile can declare a client with a single ``<records>`` node.

    ``client_id`` and ``auth_method`` are not here. The first is the record
    prefix, so it cannot be edited without being a different client; the
    second is decided by whether a secret was minted, which is a fact about
    registration rather than a setting. Neither has ever been editable, and a
    form offering them would be offering to break every token already issued.
    """

    title = schema.TextLine(
        title=_("Title"),
        description=_(
            "Shown to the user on the consent screen, which is the one place "
            "a person decides whether to trust this client. A client id is "
            "not a name."
        ),
        required=True,
    )

    enabled = schema.Bool(
        title=_("Enabled"),
        description=_(
            "Whether this client may obtain tokens at all. Disabling keeps "
            "the registration and its secret, and refuses every grant."
        ),
        required=False,
        default=True,
    )

    redirect_uris = schema.Tuple(
        title=_("Redirect URIs"),
        description=_(
            "Where this client may be sent back to, matched exactly. One per "
            "entry: https, a loopback address for a native app, or a "
            "private-use scheme. A fragment is refused, and so is a wildcard "
            "-- neither can ever match."
        ),
        value_type=schema.TextLine(constraint=is_redirect_uri),
        required=False,
        missing_value=(),
        default=(),
    )
    directives.widget("redirect_uris", frontendOptions={"widget": "token"})

    grant_types = schema.Tuple(
        title=_("Grants"),
        description=_(
            "Which flows this client may use. Only what the token endpoint "
            "implements is offered, so a registration cannot name a grant "
            "that would be refused later."
        ),
        value_type=schema.Choice(vocabulary=GRANTS),
        required=False,
        missing_value=(),
        default=("authorization_code",),
    )

    scope = schema.Tuple(
        title=_("Scopes"),
        description=_(
            "What this client may ask for. Only what this server issues is "
            "offered, so a registration cannot name a scope that would be "
            "narrowed away later. A request for anything outside this is "
            "narrowed rather than refused."
        ),
        value_type=schema.Choice(vocabulary=SCOPES_VOCABULARY),
        required=False,
        missing_value=(),
        default=(),
    )

    service_user = schema.TextLine(
        title=_("Acts as"),
        description=_(
            "The Plone user a client-credentials token acts as. Only "
            "meaningful for a client registered for that grant, which has no "
            "person behind it and would otherwise act as nobody."
        ),
        required=False,
        default="",
    )

    secret_hash = schema.TextLine(
        title=_("Secret hash"),
        description=_(
            "Never edited and never shown. The secret itself exists once, in "
            "the response that registered or rotated it."
        ),
        required=False,
        default="",
    )
    directives.omitted("secret_hash")

    auth_method = schema.TextLine(
        title=_("Token endpoint authentication"),
        description=_(
            "How this client authenticates at the token endpoint. Decided by "
            "whether it was registered with a secret."
        ),
        required=False,
        default=PUBLIC_AUTH_METHOD,
    )
    directives.omitted("auth_method")

    model.fieldset(
        FLOW_FIELDSET,
        label=_("Flow"),
        fields=["redirect_uris", "grant_types", "scope", "service_user"],
    )


__all__ = [
    "FLOW_FIELDSET",
    "GRANTS",
    "LOOPBACK_HOSTS",
    "LOOPBACK_SUFFIX",
    "SAFE_SCHEMES",
    "IClientRecords",
    "is_loopback",
    "is_redirect_uri",
]
