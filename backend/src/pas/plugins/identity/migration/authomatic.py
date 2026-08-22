"""Migrating from ``pas.plugins.authomatic``.

The good news, established by reading its source rather than remembering it:
authomatic already stores exactly the mapping this package stores. Its plugin
keeps ``_userid_by_identityinfo``, a BTree of
``(provider_name, provider_userid) -> userid``. That is the identity join,
ready to read. Nothing has to be reconstructed and nothing has to be inferred.

Its four user-id factories -- provider user id, provider username, username or
id, and uuid -- all produce opaque strings that are already stored against the
identity. A migration that preserves the user id verbatim is therefore correct
in every mode, which is why nothing here branches on which mode a site used.
The user ids come across unchanged, so every local role, every sharing
setting and every piece of content ownership keeps pointing at the right
person.

What does *not* come across:

**Passwords.** authomatic gives each user a random ``_secret`` and uses it as
a password. It is not something a human knows or could type, so carrying it
over would move a credential nobody can use. Users sign in through their
provider exactly as before.

**Provider secrets.** The client id and secret are read from authomatic's
configuration and written into the new provider record, because without them
nothing can log in. Everything else in its per-provider configuration --
property maps, class references, scopes expressed in its own vocabulary -- is
left behind deliberately: translating it silently would produce a provider
that looks configured and behaves differently.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.migration import Report
from plone import api
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin


#: Object id authomatic's plugin is installed under. It refuses to install
#: under any other, so this is the only place it can be.
AUTHOMATIC_PLUGIN_ID = "authomatic"

#: authomatic provider names mapped onto this package's drivers. A name that
#: is not here is migrated onto the generic OIDC driver and reported, because
#: guessing at a driver produces a provider that looks configured and is not.
DRIVER_FOR_PROVIDER = {
    "github": "github",
    "google": "google",
}

#: Driver used for anything not in the table above.
FALLBACK_DRIVER = "oidc-generic"


def _authomatic_plugin() -> BasePlugin | None:
    """Return the installed authomatic plugin, if there is one.

    :returns: The plugin, or ``None``.
    """
    acl_users = api.portal.get_tool("acl_users")
    return acl_users.get(AUTHOMATIC_PLUGIN_ID)


def _authomatic_config() -> JSONDict:
    """Return authomatic's provider configuration.

    Read through its own helper so the JSON parsing, the class resolution and
    the id assignment are all theirs. Reimplementing that here would be a
    second copy of a format we do not own.

    :returns: Mapping of provider name to configuration, empty when unset.
    """
    try:
        from pas.plugins.authomatic.utils import authomatic_cfg
    except ImportError:
        # The migration is being run in a site that never had authomatic
        # installed, which is a fine thing to attempt and a no-op.
        return {}
    return authomatic_cfg() or {}


def _provider_records(config: JSONDict, report: Report) -> list[ProviderConfig]:
    """Translate authomatic's provider configuration into ours.

    :param config: authomatic's configuration.
    :param report: Report to record notes on.
    :returns: Provider records to add.
    """
    records = []
    for name, settings in sorted(config.items()):
        driver_id = DRIVER_FOR_PROVIDER.get(name, FALLBACK_DRIVER)
        if driver_id is FALLBACK_DRIVER:
            report.skipped.append(
                f"provider {name!r}: no matching driver, migrated onto "
                f"{FALLBACK_DRIVER!r} and needs its discovery URL set by hand"
            )
        records.append(
            ProviderConfig(
                provider_id=name,
                driver_id=driver_id,
                title=settings.get("display", {}).get("name", "") or name.title(),
                enabled=True,
                config={
                    "client_id": settings.get("consumer_key", ""),
                    "client_secret": settings.get("consumer_secret", ""),
                },
            )
        )
    return records


def _identity_pairs(plugin: BasePlugin) -> list[tuple[str, str, str]]:
    """Return every ``(provider, subject, userid)`` authomatic knows.

    Reads ``_userid_by_identityinfo`` directly. Its keys are already
    ``(provider_name, provider_userid)`` tuples, so this is a transcription
    rather than a derivation -- see the module docstring.

    :param plugin: The authomatic plugin.
    :returns: The triples, sorted for a stable report.
    """
    pairs = []
    for (provider, subject), userid in plugin._userid_by_identityinfo.items():
        pairs.append((provider, str(subject), userid))
    return sorted(pairs)


def _claims_for(plugin: BasePlugin, userid: str, provider: str) -> Claims:
    """Build a claims snapshot from authomatic's stored user data.

    Best effort on purpose. The snapshot is a convenience -- the next login
    refreshes it from the provider -- so a provider whose stored shape we do
    not recognise yields an empty snapshot rather than a failed migration.

    :param plugin: The authomatic plugin.
    :param userid: The user id.
    :param provider: The provider name.
    :returns: A claims mapping.
    """
    identities = plugin._useridentities_by_userid.get(userid)
    if identities is None:
        return {}
    identity = identities.identity(provider)
    if identity is None:
        return {}
    return {
        "fullname": identity.get("name") or "",
        "email": identity.get("email") or "",
        # Never inherited as verified. authomatic did not record whether the
        # provider asserted it, and auto-linking will not act on a claim we
        # cannot trace to a verification this site performed.
        "email_verified": False,
        "username": identity.get("username") or "",
        "raw": {},
    }


def migrate(dry_run: bool = True) -> Report:
    """Migrate identities and provider configuration from authomatic.

    Idempotent: an identity this package already knows is left alone and
    reported as skipped, so a second run does nothing.

    :param dry_run: Report what would happen and write nothing. On by
        default, because the alternative default is a function that rewrites
        a site's authentication when somebody calls it to see what it does.
    :returns: What was done, or would be.
    """
    report = Report(dry_run=dry_run)

    plugin = _authomatic_plugin()
    if plugin is None:
        report.refusals.append(
            "No authomatic plugin in acl_users; there is nothing to migrate."
        )
        return report

    identity_plugin = api.portal.get_tool("acl_users").get(PLUGIN_ID)
    if identity_plugin is None:
        report.refusals.append(
            "pas.plugins.identity is not installed in this site; install it "
            "before migrating onto it."
        )
        return report

    config = _authomatic_config()
    existing = {record.provider_id for record in get_providers()}
    new_records = [
        record
        for record in _provider_records(config, report)
        if record.provider_id not in existing
    ]
    for record in new_records:
        report.providers.append(record.provider_id)

    store = identity_plugin.store
    for provider, subject, userid in _identity_pairs(plugin):
        if store.userid_for(provider, subject) is not None:
            report.skipped.append(f"identity {provider}:{subject} is already migrated")
            continue
        report.identities.append((provider, subject, userid))

    if dry_run:
        return report

    if new_records:
        set_providers([*get_providers(), *new_records])
    for provider, subject, userid in report.identities:
        store.add(provider, subject, userid, _claims_for(plugin, userid, provider))

    logger.info(
        "Migrated %d identities and %d providers from authomatic",
        len(report.identities),
        len(report.providers),
    )
    return report


__all__ = ["AUTHOMATIC_PLUGIN_ID", "migrate"]
