"""Moving accounts in and out of a site as JSON.

Three jobs, all of them the same shape -- a document in this package's format
on one side, a Plone site on the other:

:mod:`~pas.plugins.identity.exportimport.exporter`
    A site's users, groups and identities as a document.

:mod:`~pas.plugins.identity.exportimport.importer`
    A document into a site: groups first, then users, then the identity join.

:mod:`~pas.plugins.identity.exportimport.authomatic`
    A dump taken from ``pas.plugins.authomatic`` converted into a document,
    so that migrating from it is the ordinary import rather than a second
    code path.

**Why this is not the migration package.**
:mod:`pas.plugins.identity.migration` moves a site *in place*: both plugins are
installed in the same Zope instance and the identity join is copied from one
to the other. That is the right tool when there is one site and it is staying
put. It cannot help when the old site is a database you were handed, when the
new site is somewhere else entirely, or when the thing you want is a copy of
your accounts that outlives the instance. This package is for those.

**Why a document rather than GenericSetup.** The subject here is principals,
not configuration. A userid has to survive the trip verbatim -- every local
role, every ownership and every sharing entry in the target site is written
against it -- and it has to be reviewable before it is applied, by an operator
with a text editor, on a machine that is not running Plone. A single JSON file
is the only one of the available shapes that is all three.

**Everything is a function first.** The CLI in
:mod:`~pas.plugins.identity.exportimport.cli` is a thin argument parser over
:func:`export_site` and :func:`import_site`; anything it can do can be done
from a script, which is how anybody with a site that does not fit the general
case will end up doing it.
"""

from pas.plugins.identity.exportimport.authomatic import convert_authomatic
from pas.plugins.identity.exportimport.exporter import export_site
from pas.plugins.identity.exportimport.importer import import_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import Result
from pas.plugins.identity.exportimport.schema import validate


__all__ = [
    "DOCUMENT_VERSION",
    "ExportImportError",
    "Result",
    "convert_authomatic",
    "export_site",
    "import_site",
    "validate",
]
