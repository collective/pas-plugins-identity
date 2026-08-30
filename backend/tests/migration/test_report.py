"""The migration report.

Small, and worth its own tests because it is the only thing an operator reads
before deciding to commit a hard cutover.
"""

from pas.plugins.identity.migration import Report


class TestReport:
    def test_a_fresh_report_is_a_dry_run(self):
        """The safe default, matching the migrate() signature."""
        assert Report().dry_run is True

    def test_a_fresh_report_has_not_refused(self):
        """Nothing has gone wrong yet."""
        assert Report().refused is False

    def test_a_refusal_makes_it_refused(self):
        """One is enough."""
        report = Report()
        report.refusals.append("no")

        assert report.refused is True

    def test_as_dict_carries_the_counts(self):
        """So a view can render a summary without recounting."""
        report = Report(dry_run=False)
        report.identities.append(("github", "1", "userid"))
        report.providers.append("github")
        report.users.append("userid")
        report.skipped.append("something")

        body = report.as_dict()

        assert body["counts"] == {
            "identities": 1,
            "providers": 1,
            "users": 1,
            "skipped": 1,
        }

    def test_as_dict_carries_the_users(self):
        """A migration produces people as well as identities, and an operator
        reading the report wants to know how many."""
        report = Report(dry_run=False)
        report.users.append("userid")

        assert report.as_dict()["users"] == ["userid"]

    def test_as_dict_renders_triples_as_lists(self):
        """Tuples are not JSON; a view should not have to convert them."""
        report = Report()
        report.identities.append(("github", "1", "userid"))

        assert report.as_dict()["identities"] == [["github", "1", "userid"]]

    def test_as_dict_reports_the_mode(self):
        """The single most important line of the report."""
        assert Report(dry_run=False).as_dict()["dry_run"] is False
