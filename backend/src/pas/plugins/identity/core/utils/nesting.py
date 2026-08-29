"""Groups inside groups.

A group carries ``group_ids`` like a user does, and it means the same thing:
the groups this principal belongs to. So a group named there is an *outer*
group, and everybody in the inner group is in the outer one -- the way a
GitHub child team's members inherit the parent team's access.

**Why this used to be refused.** The original note said a group whose members
are groups makes ``getGroupsForPrincipal`` recursive, and that a recursive
answer computed from catalog metadata stops being a single lookup. Both halves
are true and neither is fatal, because the recursion is not over the thing
that is large. A site has as many users as it has people and as many groups as
it has teams; the group graph is the small one, it is entirely in catalog
*metadata*, and one query returns all of it. So the walk here reads every
group brain once -- one query, no object loads -- and then closes over an
in-memory mapping. The cost does not grow with the number of users, which is
the number that grows.

**Cycles are expected, not exceptional.** Nothing stops an operator putting A
in B and B in A, through two edit forms that each looked reasonable on their
own. A cycle is not an error here: it means both groups grant each other, and
the closure below is written to terminate on one rather than to detect and
refuse it. Refusing would mean the second edit form failing for a reason about
the first.

**Inactive groups do not conduct.** A group in a state outside
``group_enumeration_states`` grants nothing, and it also does not pass
membership through: deactivating a group has to remove the access of everybody
who reached something *through* it, or deactivating is not a control.
"""

#: Ceiling on how deep the walk goes before giving up on it.
#:
#: Not a cycle guard -- ``seen`` is that, and it is exact. This is the second
#: kind of runaway: a graph that is acyclic and absurd, built by an import
#: rather than by a person. Bounded so that a pathological site degrades into
#: missing a grant rather than into a request that never returns.
MAX_DEPTH = 20


def build_edges(brains) -> dict[str, tuple[str, ...]]:
    """Return the group graph, keyed by group id.

    :param brains: Group brains, already filtered to the active states.
    :returns: Group id to the ids of the groups it is a member of. Only the
        groups present in ``brains`` appear as keys, so an edge pointing at a
        deactivated or deleted group is simply not followed.
    """
    return {
        brain.group_id: tuple(getattr(brain, "group_ids", None) or ())
        for brain in brains
    }


def close_over(
    claimed: tuple[str, ...], edges: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Return every group reachable from a principal's direct memberships.

    Breadth-first from what the principal claims, following each group's own
    ``group_ids``. A group the graph does not know about is dropped rather
    than carried: it is either deleted or inactive, and both mean it grants
    nothing.

    :param claimed: The group ids stored on the principal, unfiltered.
    :param edges: The group graph, as :func:`build_edges` returns it.
    :returns: Every active group the principal is in, directly or through a
        nesting, sorted so the answer is stable across calls.
    """
    seen: set[str] = set()
    frontier = [group_id for group_id in claimed if group_id in edges]
    depth = 0
    while frontier and depth < MAX_DEPTH:
        nxt = []
        for group_id in frontier:
            if group_id in seen:
                # The cycle guard. A group already answered for cannot add
                # anything, whichever way round the edges were typed in.
                continue
            seen.add(group_id)
            nxt.extend(parent for parent in edges.get(group_id, ()) if parent in edges)
        frontier = nxt
        depth += 1
    return tuple(sorted(seen))


def members_of(group_id: str, edges: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return the group ids whose members are also members of one group.

    The other direction, and the one a members listing needs: given an outer
    group, which inner groups feed into it. The outer group itself is in the
    answer, so a caller can ask the catalog for ``group_ids=<result>`` in a
    single query rather than one per level.

    :param group_id: The outer group.
    :param edges: The group graph, as :func:`build_edges` returns it.
    :returns: ``group_id`` and every group nested under it, at any depth,
        sorted.
    """
    if group_id not in edges:
        return ()
    # Inverted once per call rather than kept: the graph is read fresh from
    # brains each time, and an index that outlived one request would be a
    # cache with no invalidation.
    children: dict[str, list[str]] = {}
    for inner, outers in edges.items():
        for outer in outers:
            children.setdefault(outer, []).append(inner)

    seen: set[str] = set()
    frontier = [group_id]
    depth = 0
    while frontier and depth < MAX_DEPTH:
        nxt = []
        for current in frontier:
            if current in seen:
                continue
            seen.add(current)
            nxt.extend(children.get(current, ()))
        frontier = nxt
        depth += 1
    return tuple(sorted(seen))


__all__ = ["MAX_DEPTH", "build_edges", "close_over", "members_of"]
