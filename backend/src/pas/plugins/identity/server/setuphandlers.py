"""Install and uninstall of the ``server`` GenericSetup profile.

The only thing that cannot be done declaratively is the signing key: it has to
be generated, not shipped, or every site running this add-on would sign its
tokens with the same key as every other one.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.server.keys import ensure_keys
from Products.GenericSetup.tool import SetupTool


def post_install(context: SetupTool) -> None:
    """Generate a signing key if the site has none.

    Idempotent: re-applying the profile must not rotate the key underneath
    tokens that are still inside their lifetime. Rotation is a deliberate act
    from the control panel, never a side effect of reinstalling.

    :param context: The setup tool running the import.
    """
    keys = ensure_keys()
    logger.info(
        "Authorization server ready with %s signing key(s); active kid %s",
        len(keys),
        keys[0]["kid"],
    )


def post_uninstall(context: SetupTool) -> None:
    """Report what uninstalling leaves behind.

    The registry records go with ``registry.xml``, and that includes the key
    ring -- which is the point: a site that removes the authorization server
    should stop being able to sign as itself. Any token still in flight stops
    verifying, which is the correct outcome and worth saying out loud, because
    it is not recoverable by reinstalling.

    :param context: The setup tool running the import.
    """
    logger.info(
        "Authorization server uninstalled; the signing keys are gone and "
        "tokens minted with them will no longer verify"
    )
