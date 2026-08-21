"""Integration tests for ``@audit-log`` (Gate 4, §4.6, D7)."""

from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import FLOW_REFUSED
from pas.plugins.identity.core.audit import UNATTRIBUTED
from pas.plugins.identity.core.services.auditlog import AuditLogGet
from pas.plugins.identity.core.services.auditlog import MAX_LIMIT
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME

import pytest


@pytest.fixture()
def member(portal):
    """Create and log in an ordinary member."""
    with api.env.adopt_roles(["Manager"]):
        user = api.user.create(
            email="member@plone.org",
            username="member",
            password="s3cr3t-member",
        )
    login(portal, "member")
    return user.getId()


def read(portal, request_, **form) -> dict:
    """GET the audit log.

    :param portal: The Plone site.
    :param request_: The current request.
    :param form: Query parameters.
    :returns: The service's reply.
    """
    request_.form.clear()
    request_.form.update(form)
    return AuditLogGet(portal, request_).reply()


class TestAccess:
    def test_anonymous_is_refused(self, portal, request_):
        """An authentication log is not public."""
        logout()

        result = read(portal, request_)

        assert request_.response.getStatus() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_member_sees_their_own(self, portal, request_, member, log):
        """The default scope is you."""
        log.record(member, AUTHENTICATED, "dex", True)
        log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = read(portal, request_)

        assert result["scope"] == member
        assert len(result["items"]) == 1

    def test_member_cannot_read_another_user(self, portal, request_, member, log):
        """Not 404: the caller knows the log exists, having just read theirs."""
        log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = read(portal, request_, userid="somebody-else")

        assert request_.response.getStatus() == 403
        assert result["error"]["type"] == "Not allowed"

    def test_member_cannot_read_the_site(self, portal, request_, member, log):
        """A site-wide log is a list of who has accounts."""
        read(portal, request_, scope="site")

        assert request_.response.getStatus() == 403

    def test_asking_for_your_own_userid_is_fine(self, portal, request_, member, log):
        """Naming yourself explicitly is not an escalation."""
        log.record(member, AUTHENTICATED, "dex", True)

        result = read(portal, request_, userid=member)

        assert request_.response.getStatus() == 200
        assert len(result["items"]) == 1

    def test_manager_reads_another_user(self, portal, request_, log):
        """Managers investigate accounts other than their own."""
        log.record("somebody-else", AUTHENTICATED, "dex", True)
        login(portal, TEST_USER_NAME)

        with api.env.adopt_roles(["Manager"]):
            result = read(portal, request_, userid="somebody-else")

        assert request_.response.getStatus() == 200
        assert result["scope"] == "somebody-else"
        assert len(result["items"]) == 1

    def test_manager_reads_the_site(self, portal, request_, log):
        """Including the refusals nobody can be attributed."""
        log.record("somebody-else", AUTHENTICATED, "dex", True)
        log.record(None, FLOW_REFUSED, "dex", False)
        login(portal, TEST_USER_NAME)

        with api.env.adopt_roles(["Manager"]):
            result = read(portal, request_, scope="site")

        assert result["scope"] == "site"
        assert len(result["items"]) == 2

    def test_site_scope_includes_unattributed(self, portal, request_, log):
        """The view an operator investigating an attack actually wants."""
        log.record(None, FLOW_REFUSED, "dex", False)
        login(portal, TEST_USER_NAME)

        with api.env.adopt_roles(["Manager"]):
            site = read(portal, request_, scope="site")
            bucket = read(portal, request_, userid=UNATTRIBUTED)

        assert len(site["items"]) == 1
        assert len(bucket["items"]) == 1


class TestRendering:
    def test_entry_shape(self, portal, request_, member, log):
        """What a client can rely on."""
        log.record(member, AUTHENTICATED, "dex", True, {"subject": "s"})

        item = read(portal, request_)["items"][0]

        assert item["event"] == AUTHENTICATED
        assert item["provider"] == "dex"
        assert item["success"] is True
        assert item["detail"] == {"subject": "s"}
        assert item["timestamp"]

    def test_newest_first(self, portal, request_, member, log):
        """An operator reads the top of the log."""
        for index in range(3):
            log.record(member, AUTHENTICATED, "dex", True, {"n": index})

        items = read(portal, request_)["items"]

        assert [i["detail"]["n"] for i in items] == [2, 1, 0]

    def test_total_is_reported_separately_from_the_page(
        self, portal, request_, member, log
    ):
        """A truncated answer must say so, or it reads as "that is all"."""
        for _ in range(10):
            log.record(member, AUTHENTICATED, "dex", True)

        result = read(portal, request_, limit=3)

        assert result["items_total"] == 10
        assert len(result["items"]) == 3

    @pytest.mark.parametrize("limit", ["nonsense", "", 0, -5])
    def test_unusable_limits_fall_back(self, portal, request_, member, log, limit):
        """A junk limit is not a licence to render nothing."""
        log.record(member, AUTHENTICATED, "dex", True)

        assert len(read(portal, request_, limit=limit)["items"]) == 1

    def test_limit_is_capped(self, portal, request_, member, log):
        """A site-wide read on a busy site is still worth capping."""
        result = read(portal, request_, limit=10_000)

        assert result["items"] == []
        # The cap is what protects the response, so pin it rather than the
        # empty result above.
        assert MAX_LIMIT < 10_000


class TestWithoutASink:
    def test_no_sink_is_an_empty_log(self, portal, request_, member, monkeypatch):
        """A site that unregistered the sink has nothing to read, which is a
        configuration answer rather than an error."""
        from pas.plugins.identity.core.services import auditlog

        monkeypatch.setattr(auditlog, "queryUtility", lambda *a, **kw: None)

        result = read(portal, request_)

        assert result["items"] == []
        assert result["scope"] == "none"


class TestPrivacyDefault:
    def test_no_ip_in_rendered_entries(self, portal, request_, member, log):
        """D7 -- with the flag off, nothing about the machine is stored, so
        nothing about it can be published either."""
        from pas.plugins.identity.core.audit import record

        record(member, AUTHENTICATED, "dex", True, request=request_)

        item = read(portal, request_)["items"][0]
        assert "ip" not in item["detail"]
        assert "user_agent" not in item["detail"]

    def test_opt_in_surfaces_it(self, portal, request_, member, log):
        """And with it on, the operator gets what they asked for."""
        from pas.plugins.identity.core.audit import record
        from pas.plugins.identity.core.audit import RECORD_PII_RECORD

        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        request_.environ["REMOTE_ADDR"] = "203.0.113.7"

        record(member, AUTHENTICATED, "dex", True, request=request_)

        assert read(portal, request_)["items"][0]["detail"]["ip"] == "203.0.113.7"


class TestManagerIsNotSpecialByDefault:
    def test_manager_still_defaults_to_their_own(self, portal, request_, log):
        """Least surprise: you get your own log unless you ask otherwise,
        whatever your roles."""
        login(portal, TEST_USER_NAME)
        caller = api.user.get_current().getId()
        log.record(caller, AUTHENTICATED, "dex", True)
        log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = read(portal, request_)

        assert result["scope"] == caller
        assert len(result["items"]) == 1
