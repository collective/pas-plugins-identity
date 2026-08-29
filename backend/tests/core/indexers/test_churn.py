"""Property-style churn test for the Profile catalog.

Randomized sequences of create / modify / transition / rename / move / delete,
with :func:`pas.plugins.identity.core.doctor.check` run after *every* step.
The point is not the end state -- it is that no intermediate state is wrong,
because a bug that self-corrects two operations later is still a window in
which enumeration served the wrong answer.

Seeds are fixed and parametrized rather than drawn fresh each run. A test that
picks its own randomness fails on somebody else's machine and passes on yours,
which is a worse failure than the bug it found. Adding a seed is cheap; if one
of these ever goes red, the seed in the test id reproduces it exactly.
"""

from pas.plugins.identity.core import doctor
from pas.plugins.identity.core.catalog import all_brains
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import grant_add_permission
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import PROFILE
from plone import api
from zope.lifecycleevent import modified

import pytest
import random


#: Number of operations per run. Long enough for deletes and moves to interact
#: with each other, short enough that the whole matrix stays under a second.
STEPS = 40

#: Seeds to run. Independent sequences, not repetitions of one.
SEEDS = (1, 7, 13, 42, 2026)

#: Group ids the steps draw from. A small pool on purpose: the interesting
#: sequences are the ones where a Profile lists a group that is created,
#: deleted and created again around it.
GROUP_IDS = ("editors", "reviewers", "readers")

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
            elsewhere = api.content.create(
                container=portal,
                type="Folder",
                id=f"elsewhere-{index}",
                title=f"Elsewhere {index}",
            )
            # Principals are addable only in the configured container, so a
            # folder the churn is going to move a Profile into has to be a
            # folder an operator opened up. The churn is about catalog
            # consistency, not about permissions.
            for kind in (PROFILE, GROUP):
                grant_add_permission(elsewhere, kind)
            self.folders.append(elsewhere)

    def _of_type(self, portal_type: str) -> list:
        """Return the live objects of one type.

        :param portal_type: The type to collect.
        :returns: The objects.
        """
        catalog = api.portal.get_tool("portal_catalog")
        return [
            brain._unrestrictedGetObject()
            for brain in catalog.unrestrictedSearchResults(portal_type=portal_type)
        ]

    def _groups(self) -> list:
        """Return the live Groups.

        :returns: Group objects.
        """
        return self._of_type(GROUP_PORTAL_TYPE)

    def _profiles(self) -> list:
        """Return the Profiles currently in the site.

        :returns: Live Profile objects.
        """
        return self._of_type(PROFILE_PORTAL_TYPE)

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
            group_ids=self._some_groups(),
        )

    def _some_groups(self) -> tuple:
        """Return a random subset of the group id pool.

        Drawn from the pool rather than from the groups that exist, so a
        Profile routinely names a group that is not there -- which is the
        state a deleted group leaves behind and the one the consistency check
        has an opinion about.

        :returns: Group ids.
        """
        return tuple(group_id for group_id in GROUP_IDS if self.rng.random() < 0.4)

    def _available_group_ids(self) -> list[str]:
        """Return the group ids nothing is using yet.

        :returns: Free group ids.
        """
        taken = {group.group_id for group in self._groups()}
        return [group_id for group_id in GROUP_IDS if group_id not in taken]

    def create_group(self) -> None:
        """Add a Group under an id nothing is using."""
        group_id = self.rng.choice(self._available_group_ids())
        api.content.create(
            container=self.rng.choice(self.folders),
            type=GROUP_PORTAL_TYPE,
            id=group_id,
            group_id=group_id,
            title=group_id.title(),
        )

    def transition_group(self) -> None:
        """Fire a random available transition on a random Group."""
        groups = self._groups()
        if not groups:
            return
        group = self.rng.choice(groups)
        available = [
            action["id"]
            for action in api.portal.get_tool("portal_workflow").listActionInfos(
                object=group
            )
            if action["category"] == "workflow" and action["available"]
        ]
        api.content.transition(obj=group, transition=self.rng.choice(available))

    def delete_group(self) -> None:
        """Remove a random Group, leaving whoever listed it behind."""
        groups = self._groups()
        if not groups:
            return
        api.content.delete(obj=self.rng.choice(groups))

    def regroup(self) -> None:
        """Rewrite a random Profile's memberships."""
        profile = self._pick()
        profile.group_ids = self._some_groups()
        modified(profile)

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
        creators = (
            (self.create, self.create_group)
            if self._available_group_ids()
            else (self.create,)
        )
        pool = (
            (
                self.create,
                self.create,
                self.create,
                *creators,
                self.transition_group,
                self.delete_group,
                self.regroup,
                self.modify,
                self.transition,
                self.rename,
                self.move,
                self.delete,
            )
            if self._profiles()
            else creators
        )
        operation = self.rng.choice(pool)
        operation()
        return operation


@pytest.mark.parametrize("seed", SEEDS)
class TestChurn:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_catalog_stays_consistent(self, seed: int):
        """No step leaves the catalog disagreeing with the site."""
        rng = random.Random(seed)
        churn = Churn(self.portal, rng)
        for step in range(STEPS):
            operation = churn.step()

            # UNKNOWN_GROUP is expected here and is not drift: the
            # churn deliberately has Profiles naming groups that come and
            # go, and the point is that the catalog stays consistent while
            # they do. Every other kind is a real inconsistency.
            findings = [
                finding
                for finding in doctor.check()
                if finding["kind"] != doctor.UNKNOWN_GROUP
            ]
            assert findings == [], (
                f"seed {seed}, step {step}, after {operation.__name__}"
            )

    def test_counts_agree(self, seed: int):
        """Catalog count equals Profile count, all the way through."""
        rng = random.Random(seed)
        churn = Churn(self.portal, rng)
        for step in range(STEPS):
            operation = churn.step()

            expected = len(churn._profiles()) + len(churn._groups())
            assert len(all_brains(self.catalog)) == expected, (
                f"seed {seed}, step {step}, after {operation.__name__}"
            )
