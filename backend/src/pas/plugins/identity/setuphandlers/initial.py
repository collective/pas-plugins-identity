"""The ``initial`` profile: example content for fresh sites.

Runs only during site creation, not on reinstall, to avoid duplicating content.
"""

from pas.plugins.identity import logger
from pathlib import Path
from plone import api
from plone.exportimport import importers  # type: ignore[attr-defined]
from Products.GenericSetup.tool import SetupTool


#: The export this profile imports, as written by ``plone.exportimport``.
EXAMPLE_CONTENT_FOLDER = Path(__file__).parent / "examplecontent"


def create_example_content(portal_setup: SetupTool) -> None:
    """Import example content from the examplecontent folder.

    Logs importer output as it runs to show progress during site creation.

    :param portal_setup: The setup tool running this step (unused).
    """
    # Never import principals.json
    principals = EXAMPLE_CONTENT_FOLDER / "principals.json"
    if principals.exists():
        principals.unlink()
    # Create example content
    portal = api.portal.get()
    importer = importers.get_importer(portal)
    for line in importer.import_site(EXAMPLE_CONTENT_FOLDER):
        logger.info(line)
