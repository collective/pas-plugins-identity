from pas.plugins.identity.testing import ACCEPTANCE_TESTING
from pas.plugins.identity.testing import FUNCTIONAL_TESTING
from pas.plugins.identity.testing import INTEGRATION_TESTING
from pathlib import Path
from pytest_plone import fixtures_factory
from requests import exceptions as requests_exc

import os
import pytest
import requests
import shutil


pytest_plugins = ["pytest_plone"]


@pytest.fixture
def acl_users(portal):
    """Return the site's PAS instance.

    :param portal: The Plone site.
    :returns: ``acl_users``.
    """
    return portal.acl_users


globals().update(
    fixtures_factory((
        (ACCEPTANCE_TESTING, "acceptance"),
        (FUNCTIONAL_TESTING, "functional"),
        (INTEGRATION_TESTING, "integration"),
    ))
)


#: Set this in CI. Without it a machine with no Docker skips the flow tests,
#: which is right for a laptop and quietly wrong for a pipeline: the one place
#: the end-to-end flow must actually run is the one place nobody is watching.
REQUIRE_DOCKER = "PAS_IDENTITY_REQUIRE_DOCKER"

#: Credentials of the static Dex user; see ``tests/dex/config.yaml``.
DEX_USER = {
    "email": "erico@plone.org",
    "password": "plone-test-password",
    "username": "ericof",
}


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig) -> Path:
    """Point pytest-docker at this package's compose file.

    :param pytestconfig: The pytest config, for the rootdir.
    :returns: Path to the compose file.
    """
    return Path(str(pytestconfig.rootdir)).resolve() / "tests" / "docker-compose.yml"


def _docker_available() -> bool:
    """Report whether a usable Docker daemon is reachable.

    :returns: Whether the compose stack could be started.
    """
    if (
        shutil.which("docker") is None
    ):  # pragma: no cover - environment branch: not taken on a machine that has Docker
        return False
    import subprocess

    try:
        return (
            subprocess.run(
                ["docker", "info"],  # noqa: S607
                capture_output=True,
                timeout=20,
                check=False,
            ).returncode
            == 0
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):  # pragma: no cover - defensive: a broken docker binary, not reachable with a working one
        return False


def _responsive(url: str) -> bool:
    """Report whether a URL answers 200.

    :param url: URL to poll.
    :returns: Whether the service is up.
    """
    try:
        return requests.get(url, timeout=5).status_code == 200
    except requests_exc.RequestException:  # pragma: no cover - timing branch: only taken when Dex is slower to boot than the first poll
        return False


@pytest.fixture(scope="session")
def dex_service(docker_ip, docker_services) -> str:
    """Bring up Dex and wait for it to answer.

    Only tests that ask for this fixture start the stack, so the unit and
    integration suite never touches Docker.

    :param docker_ip: Host the compose stack is reachable at.
    :param docker_services: pytest-docker's service manager.
    :returns: Dex's issuer URL.
    :raises AssertionError: When Docker is unavailable but required.
    """
    if not _docker_available():  # pragma: no cover - environment branch: the suite that measures coverage is the one that has Docker
        message = "Docker is not available; skipping the flow tests"
        if os.environ.get(REQUIRE_DOCKER):
            raise AssertionError(f"{message}, but {REQUIRE_DOCKER} is set")
        pytest.skip(message)

    # The port is fixed in the compose file rather than ephemeral: Dex
    # publishes its issuer in the discovery document and refuses to be reached
    # under any other URL, so the host port has to match dex/config.yaml.
    port = docker_services.port_for("dex", 5556)
    issuer = f"http://{docker_ip}:{port}/dex"
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: _responsive(f"{issuer}/.well-known/openid-configuration"),
    )
    return issuer


@pytest.fixture(scope="session")
def dex(dex_service: str) -> dict:
    """Return the provider record for the running Dex.

    :param dex_service: The issuer URL.
    :returns: A provider configuration as the control panel stores it.
    """
    return {
        "id": "dex",
        "driver": "oidc-generic",
        "title": "Dex",
        "enabled": True,
        "config": {
            "issuer": dex_service,
            "client_id": "plone",
            "client_secret": "plone-secret",
            "scope": "openid email profile",
        },
    }
