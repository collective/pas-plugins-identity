"""The console scripts, as far as they can be driven without a Zope instance.

``identity-exporter`` and ``identity-importer`` bring up a whole Zope app from
a ``zope.conf``, which a test suite already inside one cannot do a second time.
What *is* ours and testable is everything before that: the argument shapes, and
the four ways a run gives up before it ever reaches the site. Those are also
the paths an operator hits most, because they are the ones a typo reaches.
"""

from pas.plugins.identity.exportimport import cli

import json
import pytest


@pytest.fixture
def document(tmp_path):
    """Return a path holding a minimal valid document.

    :param tmp_path: pytest's temporary directory.
    :returns: The path.
    """
    path = tmp_path / "principals.json"
    path.write_text(json.dumps({"version": 1, "users": [], "groups": []}))
    return path


class TestTheArguments:
    """The shape matches ``plone-exporter`` and ``plone-importer``, so an
    operator who has run those does not learn a second set."""

    def test_the_exporter_takes_a_conf_a_site_and_a_path(self):
        parsed = cli._parse_args(
            cli.CLI_SPEC["exporter"],
            ["identity-exporter", "etc/zope.conf", "plone", "var/out.json"],
        )

        assert parsed.zopeconf == "etc/zope.conf"
        assert parsed.site == "plone"
        assert parsed.path == "var/out.json"

    def test_the_importer_flags_default_to_off(self):
        """A run that was not asked to be a dry run must write, and a
        document is read as ours unless it is said to be authomatic's."""
        parsed = cli._parse_args(
            cli.CLI_SPEC["importer"],
            ["identity-importer", "etc/zope.conf", "plone", "in.json"],
        )

        assert parsed.dry_run is False
        assert parsed.from_authomatic is False

    def test_allow_unknown_providers_defaults_to_off(self):
        """It turns off the guard that stops a migration nobody can sign in
        to, so it has to be asked for."""
        parsed = cli._parse_args(
            cli.CLI_SPEC["importer"],
            ["identity-importer", "etc/zope.conf", "plone", "in.json"],
        )

        assert parsed.allow_unknown_providers is False
        assert parsed.trust_verified_emails is False

    def test_the_importer_flags_can_be_set(self):
        parsed = cli._parse_args(
            cli.CLI_SPEC["importer"],
            [
                "identity-importer",
                "etc/zope.conf",
                "plone",
                "in.json",
                "--dry-run",
                "--from-authomatic",
                "--allow-unknown-providers",
                "--trust-verified-emails",
            ],
        )

        assert parsed.dry_run is True
        assert parsed.from_authomatic is True
        assert parsed.allow_unknown_providers is True
        assert parsed.trust_verified_emails is True


class TestGivingUpBeforeTheSite:
    """Each of these exits non-zero without touching Zope, which is what lets
    them be tested at all -- and what makes a typo cheap."""

    def test_the_exporter_refuses_a_directory_that_is_not_there(self, tmp_path):
        """Refused rather than created: a path with a typo in it would
        otherwise produce a directory nobody meant and a backup nobody
        finds."""
        missing = tmp_path / "nope" / "out.json"

        with pytest.raises(SystemExit) as exit_code:
            cli.exporter_cli([
                "identity-exporter",
                "etc/zope.conf",
                "plone",
                str(missing),
            ])

        assert exit_code.value.code == 1

    def test_the_importer_refuses_a_file_that_is_not_there(self, tmp_path):
        with pytest.raises(SystemExit) as exit_code:
            cli.importer_cli([
                "identity-importer",
                "etc/zope.conf",
                "plone",
                str(tmp_path / "absent.json"),
            ])

        assert exit_code.value.code == 1

    def test_the_importer_refuses_a_file_that_is_not_json(self, tmp_path):
        """Reported as bad JSON rather than as a traceback from halfway
        through a migration."""
        path = tmp_path / "broken.json"
        path.write_text("{ this is not json")

        with pytest.raises(SystemExit) as exit_code:
            cli.importer_cli(["identity-importer", "etc/zope.conf", "plone", str(path)])

        assert exit_code.value.code == 1

    def test_the_importer_refuses_a_document_that_is_not_an_authomatic_dump(
        self, document
    ):
        """``--from-authomatic`` on one of our own documents. The two formats
        are close enough that reading one as the other half-works, and the
        conversion refuses before Zope is ever started."""
        with pytest.raises(SystemExit) as exit_code:
            cli.importer_cli([
                "identity-importer",
                "etc/zope.conf",
                "plone",
                str(document),
                "--from-authomatic",
            ])

        assert exit_code.value.code == 1
