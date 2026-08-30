"""Reusable machinery for the content type tests.

Everything here is type-agnostic. A test module supplies ``portal_type`` and
``payload`` and gets the rest, so adding a third content type later means
writing a module rather than a fixture.

Two things differ from the same harness in a plainer package, and both come
from what these types are. Principals may only be created where the add
permission is granted -- which is the container the registry names, and
nowhere else -- so ``container`` resolves that rather than defaulting to the
portal. And this package is not under ``tests/core``, so the autouse fixtures
that elect those tests as a manager do not reach here; the factory elevates
for itself.
"""

from collections.abc import Callable
from collections.abc import Generator
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import PROFILE
from plone import api
from plone.dexterity.content import DexterityContent
from typing import Any
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent

import pytest


@pytest.fixture(scope="class")
def portal(portal_class):
    """Yield the class-scoped Plone site.

    Class-scoped because none of these tests writes anything another one
    reads: they ask the FTI what it declares, and the one that does create
    content cleans up after itself.

    :param portal_class: The class-scoped site from ``pytest-plone``.
    :returns: The site.
    """
    yield portal_class


@pytest.fixture(scope="session")
def content_factory() -> Callable[[DexterityContent, dict], DexterityContent]:
    """Return a factory to create content inside a container.

    :returns: Callable taking a container and a creation payload -- keys
        starting with ``_`` are dropped -- and returning the new content.
    """

    def func(container: DexterityContent, payload: dict) -> DexterityContent:
        payload = {k: v for k, v in payload.items() if not k.startswith("_")}
        with api.env.adopt_roles(["Manager"]):
            content = api.content.create(container=container, **payload)
        return content

    return func


@pytest.fixture(scope="class")
def container(portal, portal_type: str) -> DexterityContent:
    """Return the container the type under test may actually be created in.

    Not the portal. Both add permissions are granted to no role site-wide, so
    a Profile or a Group refuses to be created anywhere except the configured
    container -- which is the lock this package puts on principals, and the
    reason this fixture asks the registry instead of assuming a folder.

    :param portal: The Plone site.
    :param portal_type: The type under test, which decides which of the two
        containers is meant.
    :returns: The container.
    """
    kind = GROUP if portal_type == "UserGroup" else PROFILE
    with api.env.adopt_roles(["Manager"]):
        return get_container(create=True, kind=kind)


@pytest.fixture(scope="class")
def content_instance(
    content_factory: Callable[[DexterityContent, dict], DexterityContent],
    container: DexterityContent,
    payload: dict,
) -> Generator[DexterityContent]:
    """Create a content instance for the test class and remove it afterwards.

    :param content_factory: Factory returned by :func:`content_factory`.
    :param container: Container the content is created in.
    :param payload: Creation payload, provided by the test module.
    :returns: Generator yielding the new content object.
    """
    content = content_factory(container, payload)
    content_id = content.id
    yield content
    # Unconditional, unlike the same fixture elsewhere: no test here deletes
    # the content itself, so a guard would be a branch nothing ever takes --
    # and if one starts deleting, a loud teardown is the better answer.
    with api.env.adopt_roles(["Manager"]):
        container.manage_delObjects([content_id])


@pytest.fixture(scope="session")
def last_version() -> Callable[[DexterityContent], Any]:
    """Return a helper to retrieve the latest version of a content object.

    :returns: Callable taking a content object and returning its
        ``IVersionData`` as stored in ``portal_repository``.
    """

    def func(content: DexterityContent) -> Any:
        repo_tool = api.portal.get_tool("portal_repository")
        with api.env.adopt_roles(["Manager"]):
            return repo_tool.retrieve(content)

    return func


@pytest.fixture(scope="session")
def history() -> Callable[[DexterityContent], Any]:
    """Return a helper to retrieve the version history of a content object.

    :returns: Callable taking a content object and returning its
        ``IHistory`` as stored in ``portal_repository``.
    """

    def func(content: DexterityContent) -> Any:
        repo_tool = api.portal.get_tool("portal_repository")
        with api.env.adopt_roles(["Manager"]):
            return repo_tool.getHistory(content)

    return func


@pytest.fixture
def versionable_content_types(portal) -> list[str]:
    """Return the portal types versioning is enabled for.

    :param portal: Plone site.
    :returns: Portal type ids registered in ``portal_repository``.
    """
    repo_tool = api.portal.get_tool("portal_repository")
    return repo_tool.getVersionableContentTypes()


@pytest.fixture
def notify_modified(portal) -> Callable[[DexterityContent], None]:
    """Return a helper to fire an ``ObjectModifiedEvent`` for a content object.

    :param portal: Plone site.
    :returns: Callable taking a content object and notifying it was modified.
    """

    def func(content: DexterityContent) -> None:
        notify(ObjectModifiedEvent(content))

    return func
