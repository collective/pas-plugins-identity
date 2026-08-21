"""Property-style churn test for the Profile catalog (§8.3, Gate 6a).

Randomized sequences of create / modify / transition / rename / move / delete,
with :func:`pas.plugins.identity.profile.doctor.check` run after *every* step.
The point is not the end state -- it is that no intermediate state is wrong,
because a bug that self-corrects two operations later is still a window in
which enumeration served the wrong answer.

Seeds are fixed and parametrized rather than drawn fresh each run. A test that
picks its own randomness fails on somebody else's machine and passes on yours,
which is a worse failure than the bug it found. Adding a seed is cheap; if one
of these ever goes red, the seed in the test id reproduces it exactly.
"""

from pas.plugins.identity.profile import doctor
from pas.plugins.identity.profile.catalog import all_brains
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api
from zope.lifecycleevent import modified

import pytest
import random


#: Number of operations per run. Long enough for deletes and moves to interact
#: with each other, short enough that the whole matrix stays under a second.
STEPS = 40

#: Seeds to run. Independent sequences, not repetitions of one.
SEEDS = (1, 7, 13, 42, 2026)

#: Field values the modify step draws from. ``None`` is included on purpose:
#: clearing a field is the case where a stale brain is most visible, because
#: the catalog keeps the old value rather than obviously missing a new one.
FULLNAMES = ("Alice Liddell", "Alice L.", None)
EMAILS = ("alice@example.com", "alice@example.org", None)


class Churn:
    """Driver for one randomized sequence.

    Holds the live Profiles so the operations can pick a victim, and knows how
    to perform each one as an administrator -- the churn is about catalog
    consistency, not about permissions.
    """

    def __init__(self, portal, rng: random.Random) -> None:
        """Set up the driver.

        :param portal: The Plone site.
        :param rng: Seeded random generator.
        """
        self.portal = portal
        self.rng = rng
        self.counter = 0
        self.folders = [portal["identity-profiles"]]
        for index in range(2):
            self.folders.append(
                api.content.create(
                    container=portal,
                    type="Folder",
                    id=f"elsewhere-{index}",
                    title=f"Elsewhere {index}",
                )
            )

    def _profiles(self) -> list:
        """Return the Profiles currently in the site.

        :returns: Live Profile objects.
        """
        catalog = api.portal.get_tool("portal_catalog")
        return [
            brain._unrestrictedGetObject()
            for brain in catalog.unrestrictedSearchResults(
                portal_type=PROFILE_PORTAL_TYPE
            )
        ]

    def _pick(self):
        """Return a random existing Profile.

        Callers never have to handle "there are none": :meth:`step` only
        offers the operations that need a victim once one exists.

        :returns: A Profile.
        """
        return self.rng.choice(self._profiles())

    def create(self) -> None:
        """Add a Profile with a userid nobody else has."""
        self.counter += 1
        userid = f"user{self.counter:03d}"
        api.content.create(
            container=self.rng.choice(self.folders),
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
            fullname=self.rng.choice(FULLNAMES),
        )

    def modify(self) -> None:
        """Edit fields on a random Profile."""
        profile = self._pick()
        profile.fullname = self.rng.choice(FULLNAMES)
        profile.email = self.rng.choice(EMAILS)
        modified(profile)

    def transition(self) -> None:
        """Fire a random available transition on a random Profile."""
        profile = self._pick()
        available = [
            action["id"]
            for action in api.portal.get_tool("portal_workflow").listActionInfos(
                object=profile
            )
            if action["category"] == "workflow" and action["available"]
        ]
        # No guard on ``available`` being empty: with Manager rights every
        # state of this workflow has at least one exit, so an empty list would
        # be a bug in the workflow rather than a case to skip past quietly.
        api.content.transition(obj=profile, transition=self.rng.choice(available))

    def rename(self) -> None:
        """Give a random Profile a new id in the same folder."""
        profile = self._pick()
        self.counter += 1
        api.content.rename(obj=profile, new_id=f"renamed{self.counter:03d}")

    def move(self) -> None:
        """Move a random Profile to a different folder.

        The folder the Profile is already in is excluded from the draw
        rather than drawn and skipped: ``api.content.move`` onto the current
        parent is an error, and a skipped step is a step the sequence did not
        actually take.
        """
        profile = self._pick()
        here = profile.__parent__.getPhysicalPath()
        elsewhere = [
            folder for folder in self.folders if folder.getPhysicalPath() != here
        ]
        api.content.move(source=profile, target=self.rng.choice(elsewhere))

    def delete(self) -> None:
        """Remove a random Profile."""
        profile = self._pick()
        api.content.delete(obj=profile)

    def step(self):
        """Perform one random operation and return it.

        The pool is narrowed to :meth:`create` while the site holds no
        Profiles, rather than letting the other operations draw a victim and
        find none. A step that decides to do nothing is a step the sequence
        did not take, and forty of them can quietly become twenty.

        Creation is weighted up so a sequence does not spend most of its length
        with one Profile to churn.

        :returns: The operation that ran.
        """
        pool = (
            (
                self.create,
                self.create,
                self.create,
                self.modify,
                self.transition,
                self.rename,
                self.move,
                self.delete,
            )
            if self._profiles()
            else (self.create,)
        )
        operation = self.rng.choice(pool)
        operation()
        return operation


@pytest.mark.parametrize("seed", SEEDS)
class TestChurn:
    def test_catalog_stays_consistent(self, portal, catalog, seed):
        """No step leaves the catalog disagreeing with the site (§8.3)."""
        rng = random.Random(seed)
        with api.env.adopt_roles(["Manager"]):
            churn = Churn(portal, rng)
            for step in range(STEPS):
                operation = churn.step()

                findings = doctor.check()
                assert findings == [], (
                    f"seed {seed}, step {step}, after {operation.__name__}"
                )

    def test_counts_agree(self, portal, catalog, seed):
        """Catalog count equals Profile count, all the way through (§8.3)."""
        rng = random.Random(seed)
        with api.env.adopt_roles(["Manager"]):
            churn = Churn(portal, rng)
            for step in range(STEPS):
                operation = churn.step()

                assert len(all_brains(catalog)) == len(churn._profiles()), (
                    f"seed {seed}, step {step}, after {operation.__name__}"
                )
