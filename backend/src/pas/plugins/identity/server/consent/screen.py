"""Where the consent question is asked.

The authorization endpoint decides *whether* to ask; this decides *where*.
Two answers are possible and both are legitimate:

- **Nowhere configured.** The endpoint renders its own standalone page. That
  page exists because an authorization server has to work before anybody has
  built a frontend for it, and because a Plone site without Volto still has
  users to ask.

- **A frontend route.** The question is rendered by the site's own frontend,
  in the site's own look. A relying party sent this browser here to be asked
  something personal, and a screen that looks nothing like the site the
  person thinks they are signing in to is the screen they should not trust.

The decision is a registry record rather than something derived from the
portal URL: a frontend route is a fact about a deployment -- whether one is
served at all, and at what path -- and deriving it would mean redirecting
every consent request at a URL that may 404.
"""

from plone import api


#: Registry record naming the frontend route that renders the screen.
CONSENT_URL_RECORD = "pas.plugins.identity.server_consent_url"


def consent_screen_url() -> str:
    """Return the frontend consent screen's URL, if a site configured one.

    :returns: The URL with any trailing slash removed, so appending a query
        string produces the URL the operator meant; the empty string when no
        frontend screen is configured, which means the server renders its
        own.
    """
    configured = api.portal.get_registry_record(CONSENT_URL_RECORD, default="")
    return str(configured or "").strip().rstrip("/")


__all__ = ["CONSENT_URL_RECORD", "consent_screen_url"]
