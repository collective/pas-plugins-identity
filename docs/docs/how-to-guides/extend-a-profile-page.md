---
myst:
  html_meta:
    "description": "Render your own component on a profile or group page by registering it into one of the three slots the views expose."
    "property=og:description": "Render your own component on a profile or group page by registering it into one of the three slots the views expose."
    "property=og:title": "How to extend a profile or group page"
---

(how-to-extend-a-profile-page)=

# How to extend a profile or group page

This guide shows you how to put your own component on a profile page or a group
page without shadowing either view.

The worked example is a row of badges under somebody's name saying which teams
they belong to—the case that made the third slot exist.

## The three slots

<!-- source: frontend/packages/volto-identity/src/components/Views/BelowTitleSlot.tsx -->
<!-- source: frontend/packages/volto-identity/src/config/views.ts -->

| Slot | Renders | Rendered by |
|---|---|---|
| `aboveContent` | Above the whole view | Volto's own `View` |
| `belowTitle` | Under the heading, above the description | `BelowTitleSlot`, in each view |
| `belowContent` | Below the whole view | Volto's own `View` |

The two outer slots need nothing from this package. Both views are registered
in `config.views.contentTypesViews`, and Volto's `View` renders `aboveContent`
and `belowContent` around whatever it resolves there, so a component registered
into either reaches a profile page the day you install it.

`belowTitle` is different: nothing outside a view can place anything inside one,
so each view renders that slot itself. It is where what belongs to the person
rather than to the page reads as part of their name.

## 1. Write the component

<!-- source: frontend/packages/volto-identity/src/components/Views/BelowTitleSlot.stories.tsx -->

A slot component is an ordinary component. It is given the `content` it is
rendered for—the serialized `UserProfile` or `UserGroup`—along with `location`,
`navRoot`, and `data`.

```jsx
const TeamBadges = ({ content }) => {
  const teams = content.group_ids ?? [];
  if (!teams.length) {
    return null;
  }
  return (
    <p className="team-badges">
      {teams.map((team) => (
        <span key={team.token}>{team.title}</span>
      ))}
    </p>
  );
};

export default TeamBadges;
```

Return `null` rather than an empty element when there is nothing to draw. A slot
that renders nothing adds no markup at all, and that is the state most pages are
in.

Read the payload rather than fetching anything. A profile arrives with its
groups already on it: `group_ids` comes from the
`pas.plugins.identity.group_membership` behavior, whose field is a choice over
a vocabulary of groups, so each entry is serialized as a term—the `token` a
group is stored under, and the `title` a reader recognizes.
{doc}`/reference/profiles-and-groups` lists every field both types carry.

## 2. Register it

Register the component from your add-on's `applyConfig`, the same place you
register anything else.

```js
import TeamBadges from './components/TeamBadges';

export default function applyConfig(config) {
  config.registerSlotComponent({
    slot: 'belowTitle',
    name: 'team-badges',
    component: TeamBadges,
  });
  return config;
}
```

`name` identifies the registration within the slot, and each name renders at
most one component: the last one registered under it whose predicates all pass.
Registering your own component under a name a package you depend on used is
therefore how you replace what it renders, and a name of your own is how you
add to it.

## 3. Narrow it to the pages it belongs on

Both views render the same slot, so a component registered into `belowTitle`
appears on group pages as well as profiles. `predicates` decides where it runs:
each is a function given the same arguments as the component, and every one of
them has to return `true`.

```js
config.registerSlotComponent({
  slot: 'belowTitle',
  name: 'team-badges',
  component: TeamBadges,
  predicates: [({ content }) => content['@type'] === 'UserProfile'],
});
```

Predicates also read `location`, which is how a component is restricted to one
part of a site rather than to one content type.

## Verify

Open a profile whose owner is in at least one group. The badges are between the
heading and the biography, and the page has not otherwise changed.

Open a group page. With the predicate above, no badges are there. Take the
predicate out, reload, and they are—which is the check that the registration is
live rather than that the profile happened to render.

A profile whose owner is in no group renders exactly as it did before.

## Next steps

- {doc}`/reference/frontend`—everything the add-on registers, including the
  routes these pages live on
- {doc}`/reference/profiles-and-groups`—the fields a profile and a group carry
- {doc}`/concepts/profiles-and-groups`—why membership is stored on the member
- {doc}`install-the-frontend`—installing the add-on this extends
