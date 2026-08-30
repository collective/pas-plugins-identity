"""Console scripts, built the way ``plone.exportimport``'s are.

Two entry points, ``identity-exporter`` and ``identity-importer``, both taking
a ``zope.conf`` and a site the same way ``plone-exporter`` and
``plone-importer`` do -- an operator who has run those should not have to
learn a second set of arguments to run these.

.. code-block:: console

   $ identity-exporter etc/zope.conf plone var/principals.json
   $ identity-importer etc/zope.conf plone var/principals.json --dry-run
   $ identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic \
       --trust-verified-emails

The difference from ``plone-exporter`` is the last argument: it takes a
*directory* and writes several files into it, and this takes the path of the
one JSON file, because one file is the whole artifact.

**Everything here is a thin wrapper.** The work is in
:func:`~pas.plugins.identity.exportimport.exporter.export_site` and
:func:`~pas.plugins.identity.exportimport.importer.import_site`, which take
and return plain data. Anything this can do can be done from a script, and a
site that does not fit the general case should be scripted rather than
argued with on a command line.

**The importer commits; the exporter does not.** An export writes nothing, so
there is nothing to commit. An import commits once, at the end, after the
whole document has been applied -- so a failure part way through leaves the
site as it was rather than half-migrated. ``--dry-run`` never reaches the
commit, and never writes in the first place.
"""

from pas.plugins.identity.exportimport.authomatic import convert_authomatic
from pas.plugins.identity.exportimport.exporter import export_site
from pas.plugins.identity.exportimport.importer import import_site
from pas.plugins.identity.exportimport.schema import ExportImportError
from pathlib import Path
from plone import api
from plone.exportimport.utils import cli as cli_helpers
from zope.component import hooks

import argparse
import json
import sys
import transaction


#: Argument names and help, in the shape ``plone.exportimport`` uses so the
#: two families of command read alike.
CLI_SPEC = {
    "exporter": {
        "description": "Export a Plone site's users, groups and identities",
        "options": {
            "zopeconf": "Path to zope.conf",
            "site": "Plone site id or path to export the principals from",
            "path": "Path of the JSON file to write",
        },
        "flags": {},
    },
    "importer": {
        "description": "Import users, groups and identities into a Plone site",
        "options": {
            "zopeconf": "Path to zope.conf",
            "site": "Plone site id or path to import the principals into",
            "path": "Path of the JSON file to read",
        },
        "flags": {
            "--dry-run": "Report what would happen and write nothing",
            "--from-authomatic": (
                "Read a pas.plugins.authomatic dump rather than a document "
                "this package wrote"
            ),
            "--trust-verified-emails": (
                "Accept the addresses the source's provider called verified, "
                "without changing this site's login policy for that provider"
            ),
            "--allow-unknown-providers": (
                "Import even when this site has no provider for a name the "
                "document uses. Only for importing first and configuring the "
                "providers afterwards"
            ),
        },
    },
}


def _parse_args(spec: dict, args: list) -> argparse.Namespace:
    """Build a parser from a spec and read the arguments.

    :param spec: One entry of :data:`CLI_SPEC`.
    :param args: ``sys.argv``.
    :returns: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=spec["description"])
    for name, help_text in spec["options"].items():
        parser.add_argument(name, help=help_text)
    for name, help_text in spec["flags"].items():
        parser.add_argument(name, action="store_true", help=help_text)
    namespace, _ = parser.parse_known_args(args[1:])
    return namespace


def exporter_cli(args: list | None = None) -> None:
    """Write a site's principals to a JSON file.

    :param args: ``sys.argv``, or an equivalent list.
    """
    args = sys.argv if args is None else args
    logger = cli_helpers.get_logger("Identity Exporter")
    namespace = _parse_args(CLI_SPEC["exporter"], args)

    path = Path(namespace.path).resolve()
    if not path.parent.is_dir():
        logger.error(f"{path.parent} does not exist, please create it first.")
        sys.exit(1)

    app = cli_helpers.get_app(namespace.zopeconf)
    site = cli_helpers.get_site(app, namespace.site, logger)
    with hooks.site(site), api.env.adopt_roles(["Manager"]):
        try:
            document = export_site()
        except ExportImportError as error:
            logger.error(f" {error}")
            sys.exit(1)

    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    logger.info(f" Wrote {path}")
    logger.info(f" - {len(document['users'])} users")
    logger.info(f" - {len(document['groups'])} groups")
    logger.info(
        f" - {sum(len(user['identities']) for user in document['users'])} identities"
    )


def importer_cli(args: list | None = None) -> None:
    """Read a JSON file into a site.

    :param args: ``sys.argv``, or an equivalent list.
    """
    args = sys.argv if args is None else args
    logger = cli_helpers.get_logger("Identity Importer")
    namespace = _parse_args(CLI_SPEC["importer"], args)

    path = Path(namespace.path).resolve()
    if not path.is_file():
        logger.error(f"{path} does not exist, aborting import.")
        sys.exit(1)

    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        logger.error(f" {path} is not valid JSON: {error}")
        sys.exit(1)

    if namespace.from_authomatic:
        try:
            document = convert_authomatic(document)
        except ExportImportError as error:
            logger.error(f" {error}")
            sys.exit(1)

    app = cli_helpers.get_app(namespace.zopeconf)
    site = cli_helpers.get_site(app, namespace.site, logger)
    with hooks.site(site), api.env.adopt_roles(["Manager"]):
        logger.info(f" Reading {path} into the Plone site at /{site.id}")
        result = import_site(
            document,
            dry_run=namespace.dry_run,
            allow_unknown_providers=namespace.allow_unknown_providers,
            trust_verified_emails=namespace.trust_verified_emails,
        )
        for line in result.summary():
            logger.info(f" - {line}")
        if result.refused:
            # Nothing was written, so there is nothing to roll back -- but
            # exiting non-zero is what tells a shell script it failed.
            sys.exit(1)
        if not namespace.dry_run:
            transaction.commit()
            logger.info(" Committed.")


__all__ = ["CLI_SPEC", "exporter_cli", "importer_cli"]
