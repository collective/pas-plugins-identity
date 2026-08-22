"""Migrating from ``pas.plugins.oidc``.

Harder than the authomatic migration, and for a reason worth stating plainly:
**``pas.plugins.oidc`` stores no identity mapping at all.** Established by
reading its source, not from memory. It derives a user id as

```python
user_id = userinfo[self.getProperty("user_property_as_userid") or "sub"]
```

creates a ``source_users`` account with that id, and keeps nothing else. There
is no record that the account came from OIDC, no record of which issuer it came
from, and no record of the subject beyond the user id itself.

Two consequences shape everything here.

## The subject is only recoverable on the default setting

When ``user_property_as_userid`` is its default ``sub``, the Plone user id
*is* the subject, so ``(provider, subject) -> userid`` reconstructs exactly.

When a site changed it -- to ``email``, most likely -- the ``sub`` was never
written down and cannot be recovered from the site. Migrating such a site
correctly would mean continuing to use the same claim as the subject, which
needs a per-provider subject claim this package does not have.

So this migration **refuses** those sites rather than producing a join that
looks right. A wrong identity join does not fail at migration time; it fails
months later, as somebody logging into somebody else's account.

## Which accounts are OIDC accounts is not knowable

Since nothing marks them, this migration cannot tell an account OIDC created
from one an administrator typed in. It will not guess. Either you pass the
user ids explicitly, or you accept the default -- every ``source_users``
account -- having read the dry-run report that lists exactly which ones would
be claimed.

For a site that used OIDC exclusively, the default is right. For a mixed site
it is not, and the report is how you find that out before it matters.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.store import IdentityStore
from pas.plugins.identity.migration import Report
from plone import api
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin


#: The only ``user_property_as_userid`` value a site can be migrated from.
#: See the module docstring.
SUPPORTED_USERID_PROPERTY = "sub"

#: Driver every migrated OIDC provider lands on.
DRIVER = "oidc-generic"


def _oidc_plugins() -> list[BasePlugin]:
    """Return every OIDC plugin installed in this site.

    A site may have several, one per issuer, so this is a list rather than a
    lookup by id.

    :returns: The plugins, empty when the package is not installed.
    """
    try:
        from pas.plugins.oidc.plugins import OIDCPlugin
    except ImportError:
        return []
    acl_users = api.portal.get_tool("acl_users")
    return [
        plugin for plugin in acl_users.objectValues() if isinstance(plugin, OIDCPlugin)
    ]


def _userid_property(plugin: BasePlugin) -> str:
    """Return the claim a plugin uses as the Plone user id.

    :param plugin: An OIDC plugin.
    :returns: The claim name, defaulting as the plugin itself defaults.
    """
    return plugin.getProperty("user_property_as_userid") or SUPPORTED_USERID_PROPERTY


def _provider_record(plugin: BasePlugin) -> ProviderConfig:
    """Translate one OIDC plugin into a provider record.

    :param plugin: An OIDC plugin.
    :returns: The provider configuration.
    """
    return ProviderConfig(
        provider_id=plugin.getId(),
        driver_id=DRIVER,
        title=plugin.getProperty("title") or plugin.getId(),
        enabled=True,
        config={
            "issuer": plugin.getProperty("issuer") or "",
            "client_id": plugin.getProperty("client_id") or "",
            "client_secret": plugin.getProperty("client_secret") or "",
            "scope": " ".join(plugin.getProperty("scope") or ()),
        },
    )


def _candidate_userids(userids: list[str] | None) -> list[str]:
    """Return the user ids to claim as identities.

    :param userids: Explicit user ids, or ``None`` for every
        ``source_users`` account.
    :returns: User ids, sorted.
    """
    if userids is not None:
        return sorted(userids)
    acl_users = api.portal.get_tool("acl_users")
    source_users = acl_users.get("source_users")
    if source_users is None:
        return []
    return sorted(source_users.getUserIds())


def _check_strategies(plugins: list[BasePlugin], report: Report) -> None:
    """Refuse any plugin whose user ids do not come from ``sub``.

    See the module docstring: the subject was never stored, so the join cannot
    be reconstructed, and a wrong join surfaces later as somebody logging into
    somebody else's account.

    :param plugins: The OIDC plugins found.
    :param report: Report to record refusals on.
    """
    for plugin in plugins:
        claim = _userid_property(plugin)
        if claim != SUPPORTED_USERID_PROPERTY:
            report.refusals.append(
                f"Plugin {plugin.getId()!r} derives its user ids from the "
                f"{claim!r} claim rather than {SUPPORTED_USERID_PROPERTY!r}. "
                "The subject was never stored, so the identity join cannot be "
                "reconstructed, and a wrong join surfaces later as somebody "
                "logging into somebody else's account. Migrate this site by "
                "hand, or keep using pas.plugins.oidc."
            )


def _plan_identities(
    plugins: list[BasePlugin],
    candidates: list[str],
    store: IdentityStore,
    report: Report,
) -> None:
    """Record which identities a run would create.

    :param plugins: The OIDC plugins found.
    :param candidates: User ids to claim.
    :param store: This package's identity store.
    :param report: Report to record identities and skips on.
    """
    for plugin in plugins:
        provider = plugin.getId()
        for userid in candidates:
            # With the 'sub' strategy the Plone user id *is* the subject, which
            # is the whole reason this migration is possible at all.
            subject = userid
            if store.userid_for(provider, subject) is not None:
                report.skipped.append(
                    f"identity {provider}:{subject} is already migrated"
                )
                continue
            report.identities.append((provider, subject, userid))


def migrate(dry_run: bool = True, userids: list[str] | None = None) -> Report:
    """Migrate provider configuration and identities from ``pas.plugins.oidc``.

    Idempotent: an identity this package already knows is skipped, so a second
    run does nothing.

    :param dry_run: Report what would happen and write nothing. On by default.
    :param userids: The accounts to claim as OIDC identities. ``None`` means
        every ``source_users`` account -- correct for a site that used OIDC
        exclusively, and wrong for a mixed one. Read the dry-run report.
    :returns: What was done, or would be.
    """
    report = Report(dry_run=dry_run)

    plugins = _oidc_plugins()
    if not plugins:
        report.refusals.append(
            "No pas.plugins.oidc plugin in acl_users; there is nothing to migrate."
        )
        return report

    identity_plugin = api.portal.get_tool("acl_users").get(PLUGIN_ID)
    if identity_plugin is None:
        report.refusals.append(
            "pas.plugins.identity is not installed in this site; install it "
            "before migrating onto it."
        )
        return report

    _check_strategies(plugins, report)
    if report.refused:
        return report

    existing = {record.provider_id for record in get_providers()}
    new_records = [
        _provider_record(plugin) for plugin in plugins if plugin.getId() not in existing
    ]
    for record in new_records:
        report.providers.append(record.provider_id)

    store = identity_plugin.store
    _plan_identities(plugins, _candidate_userids(userids), store, report)

    if dry_run:
        return report

    if new_records:
        set_providers([*get_providers(), *new_records])
    for provider, subject, userid in report.identities:
        store.add(provider, subject, userid, {})

    logger.info(
        "Migrated %d identities and %d providers from pas.plugins.oidc",
        len(report.identities),
        len(report.providers),
    )
    return report


__all__ = ["DRIVER", "SUPPORTED_USERID_PROPERTY", "migrate"]
