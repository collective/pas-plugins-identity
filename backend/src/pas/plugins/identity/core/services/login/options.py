"""The providers as options of plone.restapi's ``GET @login``.

``@login`` collects ``get_providers()`` from every named
:class:`~plone.restapi.interfaces.ILoginProviders` adapter on the site, which
is how ``pas.plugins.oidc`` and ``pas.plugins.authomatic`` offer their
providers. A client written against it -- a Volto add-on, a command-line
client -- learns of ours the same way.

Each entry carries the keys the interface documents -- ``id``, ``title``,
``plugin`` and ``url`` -- plus what this package's own login page needs to
draw the button: the ``driver``, and the icon and colours grouped under
``style`` so a client can tell presentation from identity. Both listings are
built from :func:`render_provider` over the same providers, so ``@login`` and
``@login-providers`` cannot disagree about a title, a style or the order.
``supports_manual_link`` is not carried over: it is about linking a method to
an account, which no ``@login`` client does.

``flow`` says what ``url`` is, because not every provider is a redirect:

``redirect``
    ``url`` is ``@login-providers/<id>``. A ``GET`` starts an
    authorization-code flow and answers the ``authorize_url`` to send the
    browser to.
``email``
    ``url`` is ``@magic-link``. A ``POST`` with ``{"email": …}`` mails a
    single-use sign-in link; there is nowhere to send the browser. A client
    that only knows redirects should skip the entry.

A provider whose driver can do neither -- one registered by another package
with no endpoints -- is left out: there is no URL to give it.

So is everything on a site where this add-on is not installed. The adapter is
registered for the whole instance, while the services it points at are bound
to the add-on's browser layer; and uninstalling leaves the per-provider
records behind. Without the layer, every ``url`` would answer 404.
"""

from pas.plugins.identity.core.controlpanel import login_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows.metadata import has_endpoints
from pas.plugins.identity.core.interfaces import LoginFlow
from pas.plugins.identity.core.interfaces import LoginOption
from pas.plugins.identity.core.services.login import render_provider
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.interfaces import IBrowserLayer
from plone.restapi.interfaces import ILoginProviders
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFPlone.Portal import PloneSite
from typing import Literal
from zope.component import adapter
from zope.globalrequest import getRequest
from zope.interface import implementer


#: What ``plugin`` says in every entry, telling a client whose flow it is.
PLUGIN: Literal["identity"] = "identity"

#: ``flow`` for a provider whose ``url`` starts an authorization-code flow.
FLOW_REDIRECT: LoginFlow = "redirect"

#: ``flow`` for the email provider, whose ``url`` mails a magic link.
FLOW_EMAIL: LoginFlow = "email"


@implementer(ILoginProviders)
@adapter(ISiteRoot)
class LoginOptions:
    """Offer the login page's providers to ``GET @login``."""

    def __init__(self, context: PloneSite) -> None:
        """Bind the adapter.

        :param context: The site the providers are configured on.
        """
        self.context = context

    def get_providers(self) -> list[LoginOption]:
        """Return one option per provider the login page offers.

        :returns: Entries in the order the login page shows them; none when
            the add-on is not installed on this site.
        """
        if not IBrowserLayer.providedBy(getRequest()):
            return []
        portal_url = self.context.absolute_url()
        base = f"{portal_url}/@login-providers"
        options: list[LoginOption] = []
        for provider in login_providers():
            flow = self._flow(provider)
            if flow is None:
                continue
            entry = render_provider(base, provider)
            url = (
                str(entry["@id"])
                if flow == FLOW_REDIRECT
                else f"{portal_url}/@magic-link"
            )
            options.append(
                LoginOption(
                    id=provider.provider_id,
                    plugin=PLUGIN,
                    title=str(entry["title"]),
                    url=url,
                    flow=flow,
                    driver=provider.driver_id,
                    style=provider.style(),
                )
            )
        return options

    @staticmethod
    def _flow(provider: ProviderConfig) -> LoginFlow | None:
        """Return how a provider's sign-in starts.

        :param provider: The provider.
        :returns: :data:`FLOW_REDIRECT`, :data:`FLOW_EMAIL`, or ``None`` for a
            provider with no way to start at all.
        """
        if has_endpoints(provider):
            return FLOW_REDIRECT
        if provider.driver_id == EMAIL_PROVIDER:
            return FLOW_EMAIL
        return None
