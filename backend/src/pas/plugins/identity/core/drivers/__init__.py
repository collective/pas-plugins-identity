"""Provider drivers.

A driver is static metadata plus claim normalization -- it never performs I/O
and never touches the ZODB, which is what makes the whole layer unit-testable
against recorded payload fixtures with no provider in the loop.

There is one module per driver, and every one of them subclasses
:class:`~pas.plugins.identity.core.drivers.base.BaseDriver`. Drivers are
registered as named ZCA utilities; the name is the ``driver_id``. Third
parties add drivers by registering their own utility.
"""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import IDriver
from zope.component import getUtilitiesFor
from zope.component import queryUtility


def get_driver(driver_id: str) -> BaseDriver | None:
    """Look up a registered driver.

    :param driver_id: The driver id, e.g. ``github``.
    :returns: The driver utility, or ``None`` when not registered.
    """
    return queryUtility(IDriver, name=driver_id)


def all_drivers() -> dict[str, BaseDriver]:
    """Return every registered driver, keyed by id.

    :returns: Mapping of driver id to driver utility.
    """
    return dict(getUtilitiesFor(IDriver))
