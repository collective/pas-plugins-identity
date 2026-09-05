"""Fixtures for the screenshot scripts.

The scripts drive the demo stack, because it is the one deployment of this
package that anybody can start from this repository with one command and that
contains a known set of providers, users and groups. Capturing against it means
the images agree with {doc}`/tutorials/federation-demo`, which is the page most
of them illustrate.

Start it first::

    make demo-stack-start

Authentication injects the token the REST API returns rather than filling in the
login form. The capture then does not depend on the labels of the login page,
and the scripts do not repeat that form dozens of times. The login page itself,
when it needs to appear in the documentation, is captured by a script that does
not use the ``page`` fixture.
"""

from .shot import HEIGHT
from .shot import Shot
from .shot import WIDTH
from collections.abc import Iterator

import json
import pytest
import urllib.error
import urllib.parse
import urllib.request


#: The demo's identity provider.
IDP = "http://id.localhost"

#: The demo's relying party.
RP = "http://plone.localhost"

#: Demo credentials. Public by design — see the demo package's settings module.
ADMIN = ("admin", "admin")
DEMO_USER = ("dana", "dana-demo-password")


def _token(base: str, login: str, password: str) -> str:
    """Sign in through the REST API and return a JSON web token.

    :param base: Site base URL.
    :param login: User name.
    :param password: Password.
    :returns: The token.
    :raises RuntimeError: When the site refuses the credentials.
    """
    request = urllib.request.Request(
        f"{base}/++api++/@login",
        data=json.dumps({"login": login, "password": password}).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            token = json.load(response).get("token")
    except urllib.error.HTTPError as error:  # pragma: no cover - depends on stack
        raise RuntimeError(f"{base} refused {login!r}: HTTP {error.code}") from error
    if not token:
        raise RuntimeError(f"{base} returned no token for {login!r}")
    return token


def _reachable(base: str) -> bool:
    """Report whether a site answers at all.

    :param base: Site base URL.
    :returns: ``True`` when it responds.
    """
    try:
        with urllib.request.urlopen(base, timeout=5) as response:
            return response.status < 500
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def demo_stack() -> None:
    """Skip the whole run when the demo stack is not up.

    A missing stack is a setup problem, not a failure of these scripts, and a
    wall of connection errors hides that.
    """
    missing = [base for base in (IDP, RP) if not _reachable(base)]
    if missing:
        pytest.skip(
            f"The demo stack is not answering at {', '.join(missing)}. "
            f"Start it with `make demo-stack-start` from the repository root."
        )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Pin the viewport, so every capture is framed the same.

    :param browser_context_args: Playwright's own defaults.
    :returns: The arguments with the viewport set.
    """
    return {
        **browser_context_args,
        "viewport": {"width": WIDTH, "height": HEIGHT},
        "locale": "en-US",
    }


@pytest.fixture
def anonymous_page(page):
    """A page with nobody signed in.

    Use it for the login page and anything else the documentation shows to a
    visitor.

    :param page: Playwright's page fixture.
    :returns: The page, unauthenticated.
    """
    return page


@pytest.fixture
def page_as_admin(page, request) -> Iterator:
    """A page signed in as the site administrator.

    The token is written into local storage under the key Volto reads, which is
    what makes this independent of the login form's markup.

    :param page: Playwright's page fixture.
    :param request: Used to read an optional ``site`` marker naming which of the
        two demo sites to sign in to. Defaults to the identity provider.
    :returns: The page, authenticated.
    """
    marker = request.node.get_closest_marker("site")
    base = marker.args[0] if marker else IDP
    token = _token(base, *ADMIN)

    # Volto reads the token from a **cookie**, not from local storage. Setting
    # the wrong one authenticates nothing and raises nothing: every capture then
    # silently photographs an anonymous page, which is what happened the first
    # time this was written.
    host = urllib.parse.urlparse(base).hostname
    page.context.add_cookies(
        [{"name": "auth_token", "value": token, "domain": host, "path": "/"}]
    )
    page.goto(base)
    page.wait_for_load_state("networkidle")

    # Prove it took, rather than trusting it. An anonymous page still renders.
    if page.locator("a[href^='/login']").count():
        raise RuntimeError(
            f"Signed in to {base} as {ADMIN[0]!r} and the page still offers a "
            f"login link. The capture would have been of an anonymous page."
        )
    yield page


@pytest.fixture
def shot(page) -> Shot:
    """Writes captures for this script.

    :param page: Playwright's page fixture.
    :returns: The recorder.
    """
    return Shot(page=page)


def pytest_configure(config: pytest.Config) -> None:
    """Register the markers these scripts use.

    :param config: The pytest configuration.
    """
    config.addinivalue_line("markers", "site(url): which demo site to sign in to")
