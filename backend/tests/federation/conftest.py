"""The federation stack, brought up on demand.

Driven with ``docker compose`` directly rather than through pytest-docker,
which the Dex and Keycloak stacks use. Its ``docker_services`` fixture is
session-scoped and built from a single ``docker_compose_file``, so a second
compose file in the same session would either be ignored or would fight the
first for that fixture. Two stacks means two managers.

The stack is expensive -- two Plone sites, each applying GenericSetup profiles
at start -- so it is session-scoped and only brought up by tests that ask.
"""

from ..conftest import _docker_available
from ..conftest import REQUIRE_DOCKER
from identitydemo import settings
from pathlib import Path
from requests import exceptions as requests_exc

import os
import pytest
import requests
import subprocess
import time


#: Sent on the relying party's probe. plone.restapi does not serve an
#: endpoint at all without one.
JSON_HEADERS = {"Accept": "application/json"}


@pytest.fixture(autouse=True)
def _no_importer_commits(monkeypatch):
    """Stop ``plone.exportimport`` committing inside an integration test.

    The demo handlers import their payload through ``plone.exportimport``,
    whose importers commit for real: ``IMPORTER_COMMIT_DISABLE`` is off by
    default, so ``intermediate_commits`` is true and the content importer
    ends with an unconditional ``transaction.commit()``. That is right for
    the thing it was written for -- a long import that must not hold one
    transaction open over thousands of objects -- and wrong here.

    A commit escapes the per-test rollback ``plone.app.testing`` does, so
    everything ``install_idp`` wrote stayed in the site for the rest of the
    session: the demo user most visibly, since ``tests.core`` then tried
    to create its own ``alice`` and got ``Duplicate user ID``. That is a
    failure in a module which does not import the demo, hundreds of tests
    after the one that caused it, blaming a fixture that was innocent -- and
    it is invisible to anyone running either module on its own.

    Patched on ``BaseImporter`` rather than set through the environment
    because ``plone.exportimport.settings`` reads ``os.environ`` at import
    time, which makes an environment variable a race with import order.

    :param monkeypatch: pytest's patcher.
    """
    from plone.exportimport.importers.base import BaseImporter

    monkeypatch.setattr(BaseImporter, "intermediate_commits", False)


#: Compose project name. Distinct from the default, which is the directory
#: name, so this stack cannot collide with a hand-started one.
PROJECT = "identity-federation-tests"

#: How long the two sites get to create themselves and apply their profiles.
#: Generous: this is a cold Plone site build, twice, and the second waits on
#: the first being healthy before it starts.
BOOT_TIMEOUT = 300.0


def _compose(*args: str) -> subprocess.CompletedProcess:
    """Run ``docker compose`` against the federation stack.

    :param args: Arguments after the project and file selectors.
    :returns: The completed process.
    """
    compose_file = Path(__file__).resolve().parent / "docker-compose.yml"
    return subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "compose",
            "-p",
            PROJECT,
            "-f",
            str(compose_file),
            *args,
        ],
        capture_output=True,
        check=False,
    )


def _responsive(url: str, headers: dict | None = None) -> bool:
    """Report whether a URL answers 200.

    :param url: URL to poll.
    :param headers: Request headers. The relying party's probe is a
        plone.restapi endpoint, which is not served at all without an
        ``Accept`` header it recognises -- the request is refused before it
        becomes a status code, so a probe without one waits out the whole
        timeout and reports a site that is actually up as never having
        booted.
    :returns: Whether the service is up.
    """
    try:
        return requests.get(url, headers=headers, timeout=5).status_code == 200
    except requests_exc.RequestException:  # pragma: no cover - timing branch: only taken while a site is still building itself
        return False


@pytest.fixture(scope="session")
def federation_stack() -> dict:
    """Bring up the two demo sites and wait for both to answer.

    :returns: Mapping with the ``idp`` and ``rp`` base URLs.
    :raises AssertionError: When Docker is unavailable but required, or the
        stack does not come up in time.
    """
    if not _docker_available():  # pragma: no cover - environment branch: the suite that measures coverage is the one that has Docker
        message = "Docker is not available; skipping the federation tests"
        if os.environ.get(REQUIRE_DOCKER):
            raise AssertionError(f"{message}, but {REQUIRE_DOCKER} is set")
        pytest.skip(message)

    _compose("down", "-v", "--remove-orphans")
    started = _compose("up", "-d")
    if (
        started.returncode != 0
    ):  # pragma: no cover - only reached when the image is missing or a port is held
        raise AssertionError(
            "The federation stack did not start. Build the image first with "
            f"`make demo-image-build`.\n{started.stderr.decode(errors='replace')}"
        )

    urls = {"idp": settings.IDP_PUBLIC_URL, "rp": settings.RP_PUBLIC_URL}
    deadline = time.monotonic() + BOOT_TIMEOUT
    probes = (
        (f"{urls['idp']}/.well-known/openid-configuration", None),
        (f"{urls['rp']}/@login-providers", JSON_HEADERS),
    )
    while (
        time.monotonic() < deadline
    ):  # pragma: no branch - the loop always exits through one of its two returns
        if all(_responsive(url, headers) for url, headers in probes):
            break
        time.sleep(2)
    else:  # pragma: no cover - only reached when a site never finishes booting
        _compose("down", "-v")
        raise AssertionError(
            f"The federation stack did not answer within {BOOT_TIMEOUT}s"
        )

    yield urls

    _compose("down", "-v")
