---
myst:
  html_meta:
    "description": "Make a field that holds an ordered list of strings or objects render in Volto as a table, with rows dragged by a handle and each entry edited in a dialog."
    "property=og:description": "Make a field that holds an ordered list of strings or objects render in Volto as a table, with rows dragged by a handle and each entry edited in a dialog."
    "property=og:title": "How to edit a list field as a table"
---

# How to edit a list field as a table

This guide shows you how to make a field holding an ordered list render in Volto
as a table: one row per entry, a handle to drag it by, and a dialog to edit it.

`@plone-collective/volto-identity` supplies the widgets, and your field asks for
one by name. The
examples are the two fields that use them already: a Profile's `emails`, and
`social_links` from `plonegovbr.socialmedia`.

## 1. Pick the widget

<!-- source: frontend/packages/volto-identity/src/config/widgets.ts -->

| The field holds | Widget | An entry is edited with |
|---|---|---|
| Strings, in a `schema.Tuple` or `schema.List` | `identity_string_list` | The widget of the list's `value_type` |
| Objects, in a `JSONField` | `identity_object_list` | An item schema registered in the frontend |

## 2. Ask for it from the field

<!-- source: backend/src/pas/plugins/identity/core/behaviors/email.py -->
<!-- source: plone.restapi src/plone/restapi/types/adapters.py -->

Name the widget in `frontendOptions`. This is the `emails` field:

```python
from plone.autoform.directives import widget
from plone.schema import Email
from plone.supermodel import model
from zope import schema


class IEmailAddresses(model.Schema):
    emails = schema.Tuple(
        title=_("Email addresses"),
        value_type=Email(title=_("Email")),
        required=True,
        missing_value=(),
        default=(),
    )

    widget("emails", frontendOptions={"widget": "identity_string_list"})
```

The column header and the one field in the dialog both come from `value_type`.
Here the header is `Email`, and the dialog uses Volto's email widget, validation
included. `plone.restapi` serves a `Tuple` with `uniqueItems`, so the widget
refuses an entry already on the list. It serves a `List` of text without it, and
the widget accepts a repeated entry there.

<!-- source: frontend/packages/volto-identity/src/components/Widgets/OrderedObjectListWidget/OrderedObjectListWidget.tsx -->
<!-- source: plone.restapi src/plone/restapi/types/utils.py -->
<!-- source: @plone/volto src/components/manage/Form/Field.jsx -->

For a list of objects, also pass the item schema's name, and the columns to show,
in `widgetProps`. This is `plonegovbr.socialmedia`'s `social_links` field under
another name, with `columns` added:

```python
from plone.autoform import directives
from plone.schema import JSONField
from plone.supermodel import model

import json


class ILinks(model.Schema):
    directives.widget(
        "links",
        frontendOptions={
            "widget": "identity_object_list",
            "widgetProps": {"schemaName": "links", "columns": ["id", "title"]},
        },
    )
    links = JSONField(
        title=_("Links"),
        schema=json.dumps({"type": "array", "items": {"type": "object"}}),
        default=[],
        required=False,
    )
```

`plone.restapi` serves `frontendOptions` as written, and Volto hands
`widgetProps` to the widget as props. Leave out `columns` and every field of the
item schema is a column.

## 3. Describe an entry

A list of strings skips this step.

For a list of objects, register the item schema in your project's frontend
configuration, under the name `schemaName` gives:

```js
config.registerUtility({
  name: 'links',
  type: 'schema',
  method: () => ({
    title: 'Link',
    fieldsets: [
      { id: 'default', title: 'Default', fields: ['id', 'title', 'href'] },
    ],
    properties: {
      id: {
        title: 'Network',
        choices: [
          ['github', 'GitHub'],
          ['website', 'Website'],
        ],
      },
      title: { title: 'Title' },
      href: { title: 'Target' },
    },
    required: ['id', 'title', 'href'],
  }),
});
```

`title` names one entry, so the add button here is labelled {guilabel}`Add Link`.
The method receives the props of the widget, and `props` and `intl` as keys as
well, so it can translate its titles with `intl.formatMessage`.

Volto's own `object_list` widget finds its schema through `schemaName` too, so a
field written for that widget needs no new utility.

## 4. List the add-ons in order

<!-- source: @plone/registry src/addon-registry/create-addons-loader.ts -->

Only `social_links` needs this step. `plonegovbr.socialmedia` asks for the widget
`social_media_object_list`, which both `@plonegovbr/volto-social-media` and
`@plone-collective/volto-identity` register. Add-on configuration is applied in the order the
add-ons are listed, so the last one listed wins.

In `volto.config.js`, list `@plone-collective/volto-identity` after
`@plonegovbr/volto-social-media`:

```js
const addons = [
  '@plonegovbr/volto-social-media',
  '@plone-collective/volto-identity',
];
```

The table shows each link's network and title. Its dialog is still
`@plonegovbr/volto-social-media`'s `socialMedia` schema.

## Verify

Open the edit form of an object with the field. The field is a table with a row
per entry, under a header naming the columns.

- Dragging a row by its handle moves it.
- {guilabel}`Edit` opens the entry in a dialog.
- {guilabel}`Delete` asks before it removes the row.
- The button beside the field's label opens an empty dialog for a new entry.

Nothing is stored until you save the form, so {guilabel}`Cancel` on the form
undoes all of it.

## Related

- {doc}`/reference/frontend`—every widget the add-on registers, and the props the list widgets read
- [Storybook](https://collective.github.io/pas-plugins-identity/storybook/)—the widgets rendered, without a site
- {doc}`write-a-profile-enricher`—filling a list field from what a provider sends
