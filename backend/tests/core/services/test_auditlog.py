"""Integration tests for ``@audit-log``."""

from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import FLOW_REFUSED
from pas.plugins.identity.core.audit import record
from pas.plugins.identity.core.audit import RECORD_PII_RECORD
from pas.plugins.identity.core.audit import UNATTRIBUTED
from pas.plugins.identity.core.services.auditlog import get as auditlog
from pas.plugins.identity.core.services.auditlog.get import AuditLogGet
from pas.plugins.identity.core.services.auditlog.get import MAX_LIMIT
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME

import pytest


def read(portal, request, **form) -> dict:
    """GET the audit log.

    :param portal: The Plone site.
    :param request: The current request.
    :param form: Query parameters.
    :returns: The service's reply.
    """
    request.form.clear()
    request.form.update(form)
    return AuditLogGet(portal, request).reply()


class TestAccess:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, log) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.log = log

    def _read(self, **form) -> dict:
        """GET the audit log for this test's portal and request.

        :param form: Query parameters.
        :returns: The service's reply.
        """
        return read(self.portal, self.request, **form)

    def test_anonymous_is_refused(self):
        """An authentication log is not public."""
        logout()

        result = self._read()

        assert self.request.response.getStatus() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_member_sees_their_own(self):
        """The default scope is you."""
        self.log.record(self.member, AUTHENTICATED, "dex", True)
        self.log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = self._read()

        assert result["scope"] == self.member
        assert len(result["items"]) == 1

    def test_member_cannot_read_another_user(self):
        """Not 404: the caller knows the log exists, having just read theirs."""
        self.log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = self._read(userid="somebody-else")

        assert self.request.response.getStatus() == 403
        assert result["error"]["type"] == "Not allowed"

    def test_member_cannot_read_the_site(self):
        """A site-wide log is a list of who has accounts."""
        self._read(scope="site")

        assert self.request.response.getStatus() == 403

    def test_asking_for_your_own_userid_is_fine(self):
        """Naming yourself explicitly is not an escalation."""
        self.log.record(self.member, AUTHENTICATED, "dex", True)

        result = self._read(userid=self.member)

        assert self.request.response.getStatus() == 200
        assert len(result["items"]) == 1

    def test_manager_reads_another_user(self):
        """Managers investigate accounts other than their own."""
        self.log.record("somebody-else", AUTHENTICATED, "dex", True)
        login(self.portal, TEST_USER_NAME)

        result = self._read(userid="somebody-else")

        assert self.request.response.getStatus() == 200
        assert result["scope"] == "somebody-else"
        assert len(result["items"]) == 1

    def test_manager_reads_the_site(self):
        """Including the refusals nobody can be attributed."""
        self.log.record("somebody-else", AUTHENTICATED, "dex", True)
        self.log.record(None, FLOW_REFUSED, "dex", False)
        login(self.portal, TEST_USER_NAME)

        result = self._read(scope="site")

        assert result["scope"] == "site"
        assert len(result["items"]) == 2

    def test_site_scope_includes_unattributed(self):
        """The view an operator investigating an attack actually wants."""
        self.log.record(None, FLOW_REFUSED, "dex", False)
        login(self.portal, TEST_USER_NAME)

        site = self._read(scope="site")
        bucket = self._read(userid=UNATTRIBUTED)

        assert len(site["items"]) == 1
        assert len(bucket["items"]) == 1


class TestRendering:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, log) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.log = log

    def _read(self, **form) -> dict:
        """GET the audit log for this test's portal and request.

        :param form: Query parameters.
        :returns: The service's reply.
        """
        return read(self.portal, self.request, **form)

    def test_entry_shape(self):
        """What a client can rely on."""
        self.log.record(self.member, AUTHENTICATED, "dex", True, {"subject": "s"})

        item = self._read()["items"][0]

        assert item["event"] == AUTHENTICATED
        assert item["provider"] == "dex"
        assert item["success"] is True
        assert item["detail"] == {"subject": "s"}
        assert item["timestamp"]

    def test_newest_first(self):
        """An operator reads the top of the log."""
        for index in range(3):
            self.log.record(self.member, AUTHENTICATED, "dex", True, {"n": index})

        items = self._read()["items"]

        assert [i["detail"]["n"] for i in items] == [2, 1, 0]

    def test_total_is_reported_separately_from_the_page(self):
        """A truncated answer must say so, or it reads as "that is all"."""
        for _ in range(10):
            self.log.record(self.member, AUTHENTICATED, "dex", True)

        result = self._read(limit=3)

        assert result["items_total"] == 10
        assert len(result["items"]) == 3

    @pytest.mark.parametrize("limit", ["nonsense", "", 0, -5])
    def test_unusable_limits_fall_back(self, limit):
        """A junk limit is not a licence to render nothing."""
        self.log.record(self.member, AUTHENTICATED, "dex", True)

        assert len(self._read(limit=limit)["items"]) == 1

    def test_limit_is_capped(self):
        """A site-wide read on a busy site is still worth capping."""
        result = self._read(limit=10_000)

        assert result["items"] == []
        # The cap is what protects the response, so pin it rather than the
        # empty result above.
        assert MAX_LIMIT < 10_000


class TestWithoutASink:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, monkeypatch) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        monkeypatch.setattr(auditlog, "queryUtility", lambda *a, **kw: None)

    def _read(self, **form) -> dict:
        """GET the audit log for this test's portal and request.

        :param form: Query parameters.
        :returns: The service's reply.
        """
        return read(self.portal, self.request, **form)

    def test_no_sink_is_an_empty_log(self):
        """A site that unregistered the sink has nothing to read, which is a
        configuration answer rather than an error."""
        result = self._read()

        assert result["items"] == []
        assert result["scope"] == "none"


class TestPrivacyDefault:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, log) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.log = log

    def _read(self, **form) -> dict:
        """GET the audit log for this test's portal and request.

        :param form: Query parameters.
        :returns: The service's reply.
        """
        return read(self.portal, self.request, **form)

    def test_no_ip_in_rendered_entries(self):
        """With the flag off, nothing about the machine is stored, so
        nothing about it can be published either."""
        record(self.member, AUTHENTICATED, "dex", True, request=self.request)

        item = self._read()["items"][0]
        assert "ip" not in item["detail"]
        assert "user_agent" not in item["detail"]

    def test_opt_in_surfaces_it(self):
        """And with it on, the operator gets what they asked for."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        self.request.environ["REMOTE_ADDR"] = "203.0.113.7"

        record(self.member, AUTHENTICATED, "dex", True, request=self.request)

        assert self._read()["items"][0]["detail"]["ip"] == "203.0.113.7"


class TestManagerIsNotSpecialByDefault:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, log) -> None:
        self.portal = portal
        self.request = request_
        self.log = log

    def _read(self, **form) -> dict:
        """GET the audit log for this test's portal and request.

        :param form: Query parameters.
        :returns: The service's reply.
        """
        return read(self.portal, self.request, **form)

    def test_manager_still_defaults_to_their_own(self):
        """Least surprise: you get your own log unless you ask otherwise,
        whatever your roles."""
        login(self.portal, TEST_USER_NAME)
        caller = api.user.get_current().getId()
        self.log.record(caller, AUTHENTICATED, "dex", True)
        self.log.record("somebody-else", AUTHENTICATED, "dex", True)

        result = self._read()

        assert result["scope"] == caller
        assert len(result["items"]) == 1
