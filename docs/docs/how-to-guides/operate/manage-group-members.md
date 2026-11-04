---
myst:
  html_meta:
    "description": "Add people and groups to a group, and take them out, from the group's own page."
    "property=og:description": "Add people and groups to a group, and take them out, from the group's own page."
    "property=og:title": "Manage a group's members"
---

(how-to-manage-group-members)=

# Manage a group's members

This guide shows you how to change who is in a group from the group's own page, rather than from the {guilabel}`Groups` control panel.

<!-- source: frontend/packages/volto-identity/src/components/ManageMembers/ManageMembers.tsx -->
<!-- source: backend/src/pas/plugins/identity/core/services/groups/get.py -->

## Before you start

You need the `Plone Site Setup: Users and Groups` permission.
Managers and Site Administrators have it.

A group that holds the `Manager` role can be changed by a Manager only.
`plone.restapi` refuses the change from anybody else, because adding a person to that group grants them the role.

## Open the members page

1.  Open the group.
2.  Next to {guilabel}`Members`, choose {guilabel}`Manage members`.

The button is not shown to somebody who cannot change the members.
The page is at the group's URL followed by `/manage-members`, and refuses such a caller if they go there directly.

## Add members

1.  Under {guilabel}`Add members`, type part of a name, a login, or a group's title.
2.  Tick everybody you want to add.
    What you tick is kept when you search again, so you can find several people by different names.
3.  Choose {guilabel}`Add`.

Adding a group nests it: everybody in it is then in this group too, at any depth.

## Remove members

Under {guilabel}`Direct members`, choose {guilabel}`Remove` on the row.

The list shows the groups nested here, then the people in this group itself.
Somebody who is in it only through a nested group is not listed, because they are removed from that group instead, on its own page.

A group filed inside this one in the site tree is not listed either.
No change of members undoes that nesting; moving the group does.

## What a provider's group map does afterwards

A membership a provider's group map granted can be removed here.
The provider adds it back when the set of groups it grants that person next changes, not at every sign-in.

<!-- source: backend/src/pas/plugins/identity/core/pas/plugin.py, _sync_federated_groups -->

## Verify

Open the group again.
Its members count and its list show the change straight away.

## Next steps

-   {doc}`/how-to-guides/accounts/map-provider-groups` to let a provider grant memberships instead.
-   {doc}`/reference/endpoints` for `@group-members`, which this page reads.
-   {doc}`/reference/frontend` for the requests this page sends.
-   {doc}`/concepts/profiles-and-groups` for how nesting is stored.
