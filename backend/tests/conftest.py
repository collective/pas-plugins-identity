from pas.plugins.identity.testing import ACCEPTANCE_TESTING
from pas.plugins.identity.testing import FUNCTIONAL_TESTING
from pas.plugins.identity.testing import INTEGRATION_TESTING
from pathlib import Path
from pytest_plone import fixtures_factory
from requests import exceptions as requests_exc

import itertools
import os
import pytest
import requests
import shutil
import uuid


pytest_plugins = ["pytest_plone"]


@pytest.fixture(scope="class")
def http_request_class(integration_class):
    """Return the request, for a class-scoped test.

    ``pytest_plone`` ships ``http_request``, but it depends on the
    function-scoped ``integration`` layer: asking for it from a class that
    uses ``portal_class`` tears the class-scoped layer down mid-class and
    fails with a bare ``KeyError: 'portal'``. This is the same fixture
    against the layer those classes actually run on.

    :param integration_class: The class-scoped integration layer.
    :returns: The request.
    """
    return integration_class["request"]


#: Where the demo package keeps its GenericSetup profiles.
DEMO_PROFILES = Path(__file__).parent.parent / "demo/src/identitydemo/profiles"


class _ImportEnviron:
    """The bare minimum ``RegistryImporter`` asks of its import context."""

    def getLogger(self, name: str):
        """Return a logger.

        :param name: Logger name.
        :returns: The logger.
        """
        import logging

        return logging.getLogger(name)

    def shouldPurge(self) -> bool:
        """Report whether to purge before importing.

        :returns: Always false -- a demo profile adds to a site.
        """
        return False


@pytest.fixture
def demo_registry(portal):
    """Return a callable that applies a demo profile's registry XML.

    Reading the file rather than applying the whole profile is deliberate:
    applying it would need ``identitydemo`` installed in the test site, and a
    second ``PloneSandboxLayer`` to get its ZCML loaded, which leaves two
    layers sharing one site for the rest of the session.

    :param portal: The Plone site.
    :returns: A callable taking a profile name -- ``idp`` or ``rp``.
    """
    from plone.app.registry.exportimport.handler import RegistryImporter
    from plone.registry.interfaces import IRegistry
    from zope.component import getUtility

    def apply(profile: str) -> None:
        path = DEMO_PROFILES / profile / "registry/pas.plugins.identity.xml"
        importer = RegistryImporter(getUtility(IRegistry), _ImportEnviron())
        importer.importDocument(path.read_bytes())

    return apply


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


#: How many RSA keys the pool below holds. Small: the pool exists to stop the
#: suite paying for key generation, not to model a real key ring, and every
#: draw gets its own ``kid`` regardless of which key it recycles.
KEY_POOL_SIZE = 4


@pytest.fixture(scope="session", autouse=True)
def _pooled_signing_keys():
    """Recycle a handful of RSA keys instead of minting one per site.

    Every test site that applies the ``server`` profile runs ``ensure_keys``,
    and each fresh portal therefore generated its own RSA-2048 key. Measured
    across the suite that was **520 keys and 42.9 seconds -- a fifth of the
    whole run** -- to produce material that is thrown away microseconds later.

    The expensive part is the RSA maths, not the identity, so the pool
    recycles the maths and hands out a fresh ``kid`` every time. Nothing here
    asserts on key *material*; what the ring tests assert on is the ``kid``,
    and no two draws ever share one. Signing and verification are unaffected:
    a verifier picks the key out of the JWKS by ``kid``, and a ``kid`` that is
    not in the ring fails to verify exactly as it did before.

    ``tests/server/test_keys.py`` imports ``generate_key`` by name, so its
    three tests of generation itself still exercise the real thing.

    :returns: Nothing; patches for the session and restores afterwards.
    """
    from pas.plugins.identity.server.utils import keys as keys_module

    real_generate_key = keys_module.generate_key
    pool = [real_generate_key() for _ in range(KEY_POOL_SIZE)]
    draws = itertools.count()

    def pooled() -> dict:
        """Return a pooled key under a ``kid`` nothing has used before.

        :returns: A private JWK.
        """
        key = dict(pool[next(draws) % KEY_POOL_SIZE])
        key["kid"] = uuid.uuid4().hex
        return key

    keys_module.generate_key = pooled
    yield
    keys_module.generate_key = real_generate_key


#: Set this in CI. Without it a machine with no Docker skips the flow tests,
#: which is right for a laptop and quietly wrong for a pipeline: the one place
#: the end-to-end flow must actually run is the one place nobody is watching.
REQUIRE_DOCKER = "PAS_IDENTITY_REQUIRE_DOCKER"

#: Credentials of the static Dex user; see ``tests/_resources/dex/config.yaml``.
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
    # under any other URL, so the host port has to match _resources/dex/config.yaml.
    port = docker_services.port_for("dex", 5556)
    issuer = f"http://{docker_ip}:{port}/dex"
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: _responsive(f"{issuer}/.well-known/openid-configuration"),
    )
    return issuer


@pytest.fixture(scope="session")
def keycloak_service(docker_ip, docker_services) -> str:
    """Bring up Keycloak and wait for its realm to answer.

    Dex is the provider for every other flow test and is the better one for
    the job: lighter, configured from a file, deterministic. It does not
    implement back-channel logout, though, so the single place this package
    needs a *real* provider's logout token needs a provider that sends one.

    :param docker_ip: Host the compose stack is reachable at.
    :param docker_services: pytest-docker's service manager.
    :returns: The realm's issuer URL.
    :raises AssertionError: When Docker is unavailable but required.
    """
    if not _docker_available():  # pragma: no cover - environment branch: the suite that measures coverage is the one that has Docker
        message = "Docker is not available; skipping the logout tests"
        if os.environ.get(REQUIRE_DOCKER):
            raise AssertionError(f"{message}, but {REQUIRE_DOCKER} is set")
        pytest.skip(message)

    # Fixed for the same reason Dex's is: the issuer is published in the
    # discovery document and Keycloak will not be reached under another URL.
    port = docker_services.port_for("keycloak", 8080)
    issuer = f"http://{docker_ip}:{port}/realms/identity-test"
    docker_services.wait_until_responsive(
        # Generous next to Dex's: Keycloak boots a JVM and imports a realm
        # before it answers anything.
        timeout=180.0,
        pause=1.0,
        check=lambda: _responsive(f"{issuer}/.well-known/openid-configuration"),
    )
    return issuer


@pytest.fixture(scope="session")
def keycloak(keycloak_service: str) -> dict:
    """Return the provider record for the running Keycloak.

    :param keycloak_service: The issuer URL.
    :returns: A provider configuration as the control panel stores it.
    """
    return {
        "id": "keycloak",
        "driver": "oidc-generic",
        "title": "Keycloak",
        "enabled": True,
        "config": {
            "issuer": keycloak_service,
            "client_id": "plone",
            "client_secret": "plone-secret",
            "scope": ("openid", "email", "profile"),
        },
    }


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
            "scope": ("openid", "email", "profile"),
        },
    }
