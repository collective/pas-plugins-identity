"""The demo loads Products.PrintingMailHost itself.

The Product ships no ``configure.zcml``, so its patch is reached only through
a classic ``initialize()`` gated on an environment variable. That used to be
set in ``docker-compose.demo.yml``, one file away from the dependency that
made it mean anything, and the two disagreed for a while: the package was
absent from the image and the variable was set beside it, so magic-link
sign-in answered 500 with a ``ConnectionRefusedError``.

Both halves are in this package now, and both are pinned here -- the handler
does the patching, and the ZCML actually calls it. Reading the ZCML rather
than loading it, for the reason ``test_registry_profile`` reads the registry
XML rather than applying it: loading ``identitydemo``'s configuration would
register the demo profiles for every test that runs afterwards.
"""

from identitydemo import startup
from pathlib import Path
from Products.MailHost.MailHost import MailBase

import logging
import os
import pytest


CONFIGURE_ZCML = Path(startup.__file__).parent / "configure.zcml"

#: Where the patch stores the real ``_send`` while it stands in for it. The
#: only method it replaces, and removed again when the patch is undone, so
#: its presence is exactly "this class is patched right now".
PATCHED_MARKER = "_monkey__send"


class TestSubscriberIsRegistered:
    """Nothing calls the handler unless the ZCML says so."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.zcml = CONFIGURE_ZCML.read_text()

    def test_subscribes_to_process_starting(self):
        assert 'for="zope.processlifetime.IProcessStarting"' in self.zcml

    def test_handler_is_the_one_under_test(self):
        assert 'handler=".startup.print_mail_instead_of_sending"' in self.zcml


class TestPrintMailInsteadOfSending:
    @pytest.fixture(autouse=True)
    def _unpatched(self, monkeypatch):
        """Run each test against an unpatched MailHost, and leave it that way.

        The patch is process-wide and permanent, which is the whole reason the
        handler hangs off a startup event rather than an import. A test that
        applied it and walked away would change how every later test in the
        session sends mail.
        """
        monkeypatch.delenv(startup.ENABLE_VARIABLE, raising=False)
        yield
        if hasattr(MailBase, PATCHED_MARKER):
            # Imported in here rather than at the top of the module: ``Patch``
            # logs a banner as it imports, through a global that only
            # ``initialize`` populates, so importing it before the handler has
            # run raises ``AttributeError`` on ``None``.
            from Products.PrintingMailHost.Patch import undo_patches

            undo_patches()

    def test_mailhost_sends_for_real_until_the_handler_runs(self):
        """The premise. Without this the next test proves nothing."""
        assert not hasattr(MailBase, PATCHED_MARKER)

    def test_patches_mailhost(self):
        startup.print_mail_instead_of_sending()

        assert hasattr(MailBase, PATCHED_MARKER)

    def test_sets_the_variable_when_the_environment_does_not(self):
        startup.print_mail_instead_of_sending()

        assert os.environ[startup.ENABLE_VARIABLE] == "true"

    def test_leaves_an_explicit_refusal_alone(self, monkeypatch):
        """An operator pointing the demo at a real mail server keeps it."""
        monkeypatch.setenv(startup.ENABLE_VARIABLE, "no")

        startup.print_mail_instead_of_sending()

        assert not hasattr(MailBase, PATCHED_MARKER)

    def test_says_so_when_mail_will_not_be_printed(self, monkeypatch, caplog):
        """The failure this warns about is a 500 several requests later."""
        monkeypatch.setenv(startup.ENABLE_VARIABLE, "no")

        with caplog.at_level(logging.WARNING, logger="identitydemo"):
            startup.print_mail_instead_of_sending()

        assert startup.ENABLE_VARIABLE in caplog.text

    def test_applying_twice_keeps_the_real_send(self):
        """Zope calls initialize() before this package sets the default.

        So the handler is always the *second* call, and the original has to
        survive it -- a patch that stored the patched method as the original
        would make undoing it a no-op.
        """
        startup.print_mail_instead_of_sending()
        original = getattr(MailBase, PATCHED_MARKER)

        startup.print_mail_instead_of_sending()

        assert getattr(MailBase, PATCHED_MARKER) is original
