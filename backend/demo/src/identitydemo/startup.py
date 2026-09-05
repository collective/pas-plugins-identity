"""Print the demo's e-mail to the log instead of trying to send it.

Magic-link sign-in is switched on and there is no mail server anywhere in
this stack, so a real ``MailHost`` answers a sign-in request with a 500 and a
``ConnectionRefusedError``. ``Products.PrintingMailHost`` replaces it with one
that writes the message to the log, which is where the demo's sign-in links
are meant to be read.

Loading it is this package's job rather than the image's. The Product ships no
``configure.zcml`` at all, so neither ``five:loadProducts`` nor
``CONFIGURE_PACKAGES`` has anything to say about whether it patches: its only
entry point is a classic ``initialize()`` that looks for
:data:`ENABLE_VARIABLE` in the environment. Leaving that to a compose file put
the dependency and the switch in two places that could not check each other,
and they duly disagreed -- the package went missing from the image for a
while, with the variable set beside it and nothing reading it.

Setting a *default* rather than a value, so an operator wanting to point the
demo at a real mail server still can, by setting the variable to something
falsy in the environment.

Done on ``IProcessStarting`` rather than at import time. The patch is
process-wide and permanent, and importing this package -- which the test suite
does, for the profiles -- must not quietly change what ``MailHost`` does for
everything that runs afterwards.
"""

from Products import PrintingMailHost

import logging
import os


ENABLE_VARIABLE = "ENABLE_PRINTING_MAILHOST"

logger = logging.getLogger("identitydemo")


def print_mail_instead_of_sending(event=None) -> None:
    """Patch every ``MailHost`` in the process to log messages, not send them.

    Calling ``initialize`` rather than reaching for
    :func:`Products.PrintingMailHost.Patch.apply_patches` directly: it is the
    Product's own entry point, it is what populates the module globals that
    ``Patch`` reads at import time, and it keeps
    ``PRINTING_MAILHOST_FIXED_ADDRESS`` working. Zope will have called it once
    already, before this package had a chance to set the default, and found
    nothing to do; calling it again is safe, because the patch stores each
    original attribute only the first time it replaces one.

    :param event: the ``IProcessStarting`` notification. Unused -- the handler
        needs nothing from it, and takes a default so it can be called
        directly.
    """
    os.environ.setdefault(ENABLE_VARIABLE, "true")
    PrintingMailHost.initialize(None)

    enabled = PrintingMailHost.ENABLED or ""
    if enabled.lower() in PrintingMailHost.TRUISMS:
        logger.info("Mail will be written to the log rather than sent.")
    else:
        logger.warning(
            "%s is %r, so mail will be handed to a real mail server. There is "
            "none in this stack, and magic-link sign-in will answer 500.",
            ENABLE_VARIABLE,
            enabled,
        )
