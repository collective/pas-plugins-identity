"""Ordering a provider's addresses by what a site prefers."""

from pas.plugins.identity.core.utils.address_preference import is_address_pattern
from pas.plugins.identity.core.utils.address_preference import prefer_addresses
from pas.plugins.identity.core.utils.address_preference import rank_addresses

import pytest


#: The preference from the issue that asked for this.
ISSUE_EXAMPLE = ("@plone.org", "*", "@users.noreply.github.com")


def reported(*addresses: str, verified: bool = True) -> tuple[dict, ...]:
    """Build the addresses a driver reports, in the order given.

    :param addresses: The addresses.
    :param verified: Whether the provider verified each one.
    :returns: One entry per address, the first marked primary.
    """
    return tuple(
        {"address": address, "verified": verified, "primary": index == 0}
        for index, address in enumerate(addresses)
    )


def order(entries) -> list[str]:
    """Return just the addresses, in order.

    :param entries: Reported addresses.
    :returns: Their addresses.
    """
    return [entry["address"] for entry in entries]


class TestWhatAnEntryMayBe:
    @pytest.mark.parametrize(
        "entry",
        ["*", "@plone.org", "@users.noreply.github.com", "@Plone.ORG", " @plone.org "],
    )
    def test_accepted(self, entry: str):
        assert is_address_pattern(entry) is True

    @pytest.mark.parametrize(
        "entry",
        [
            "plone.org",
            "@",
            "@plone",
            "x@plone.org",
            "*.plone.org",
            "@*.plone.org",
            "@plone..org",
            "@-plone.org",
            "",
            "**",
        ],
    )
    def test_refused(self, entry: str):
        """Each of these would match no address at all."""
        assert is_address_pattern(entry) is False

    def test_a_value_that_is_not_text_is_refused(self):
        assert is_address_pattern(None) is False


class TestRanking:
    def test_the_issue_example(self):
        """The site's domain first, everything else, then GitHub's no-reply
        address -- whatever order GitHub sent them in."""
        addresses = reported(
            "ghost@users.noreply.github.com", "ghost@gmail.com", "ghost@plone.org"
        )

        assert order(rank_addresses(addresses, ISSUE_EXAMPLE)) == [
            "ghost@plone.org",
            "ghost@gmail.com",
            "ghost@users.noreply.github.com",
        ]

    def test_a_domain_entry_is_that_domain_exactly(self):
        """Neither a subdomain nor a domain that merely ends the same way."""
        addresses = reported("a@community.plone.org", "b@notplone.org", "c@plone.org")

        ranked = order(rank_addresses(addresses, ("@plone.org",)))

        assert ranked[0] == "c@plone.org"

    def test_entries_after_the_wildcard_are_still_reachable(self):
        """``*`` is a catch-all, not a first match: it would otherwise swallow
        the no-reply address it is listed before."""
        addresses = reported("ghost@users.noreply.github.com", "ghost@gmail.com")

        ranked = order(rank_addresses(addresses, ("*", "@users.noreply.github.com")))

        assert ranked == ["ghost@gmail.com", "ghost@users.noreply.github.com"]

    def test_an_address_nothing_matches_goes_last(self):
        addresses = reported("ghost@gmail.com", "ghost@plone.org")

        ranked = order(rank_addresses(addresses, ("@plone.org",)))

        assert ranked == ["ghost@plone.org", "ghost@gmail.com"]

    def test_no_address_is_dropped(self):
        """The list orders what the provider reported; it is not a filter."""
        addresses = reported("a@gmail.com", "b@example.com", "c@plone.org")

        ranked = rank_addresses(addresses, ("@plone.org",))

        assert sorted(order(ranked)) == sorted(order(addresses))

    def test_addresses_in_the_same_place_keep_their_order(self):
        """The driver's order -- primary, then verified -- still decides
        between two addresses the preference does not tell apart."""
        addresses = reported("b@gmail.com", "a@example.com", "c@plone.org")

        ranked = order(rank_addresses(addresses, ("@plone.org", "*")))

        assert ranked == ["c@plone.org", "b@gmail.com", "a@example.com"]

    def test_an_empty_preference_keeps_the_drivers_order(self):
        addresses = reported("b@gmail.com", "c@plone.org")

        assert rank_addresses(addresses, ()) == addresses

    def test_entries_are_compared_lowercased(self):
        addresses = reported("ghost@gmail.com", "ghost@plone.org")

        assert order(rank_addresses(addresses, ("@Plone.ORG",)))[0] == "ghost@plone.org"

    def test_a_single_string_is_one_entry(self):
        """Not a sequence of one-character entries, none of which matches."""
        addresses = reported("ghost@gmail.com", "ghost@plone.org")

        assert order(rank_addresses(addresses, "@plone.org"))[0] == "ghost@plone.org"


class TestTheHeadlineAddressFollows:
    def claims(self, *addresses: str, verified: bool = True) -> dict:
        """Build claims the way a driver does: ``email`` is the head.

        :param addresses: The addresses, in the driver's order.
        :param verified: Whether each is verified.
        :returns: The claims.
        """
        emails = reported(*addresses, verified=verified)
        return {
            "email": emails[0]["address"],
            "email_verified": emails[0]["verified"],
            "emails": emails,
        }

    def test_the_preferred_address_is_the_email(self):
        claims = self.claims("ghost@users.noreply.github.com", "ghost@plone.org")

        assert prefer_addresses(claims, ISSUE_EXAMPLE)["email"] == "ghost@plone.org"

    def test_the_flag_describes_the_new_head(self):
        """A verified no-reply address and an unverified preferred one: the
        flag has to move with the address, or the pair says something neither
        half meant."""
        claims = self.claims("ghost@users.noreply.github.com", "ghost@plone.org")
        claims["emails"] = (
            {**claims["emails"][0], "verified": True},
            {**claims["emails"][1], "verified": False},
        )

        assert prefer_addresses(claims, ISSUE_EXAMPLE)["email_verified"] is False

    def test_the_claims_passed_in_are_left_alone(self):
        claims = self.claims("ghost@users.noreply.github.com", "ghost@plone.org")

        prefer_addresses(claims, ISSUE_EXAMPLE)

        assert claims["email"] == "ghost@users.noreply.github.com"

    def test_claims_with_no_addresses_are_unchanged(self):
        claims = {"email": "", "email_verified": False, "emails": ()}

        assert prefer_addresses(claims, ISSUE_EXAMPLE) is claims

    def test_nothing_to_reorder_is_the_same_claims(self):
        claims = self.claims("ghost@plone.org", "ghost@gmail.com")

        assert prefer_addresses(claims, ISSUE_EXAMPLE) is claims
