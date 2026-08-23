Rebuilt the providers control panel on Volto's own machinery, following `volto-light-theme`'s Themes panel: a table of what is configured, with Add in the toolbar rather than a form permanently open at the bottom of the page, and Save and Cancel there too while editing. Delete asks first, the connection check reports through a toast, and the page carries `id="page-controlpanel"` inside a `Container`, so it inherits every control-panel style Volto already ships.

The form is no longer written by hand. Volto's `Form` renders it from a schema built out of the driver's own `config_schema` — a secret becomes the password widget, an `int` a number, a `bool` a checkbox — so a driver added on the backend still arrives with no frontend change, and it now looks like every other control panel instead of like a stack of bare inputs. Choosing a driver rebuilds the schema, because which settings exist depends on it.

The attribute mapping is part of that schema rather than a component of its own, as an `object_list` field whose user-field column reads the `pas.plugins.identity.UserFields` vocabulary.

`ProvidersPanel`, `ProviderForm` and `PropertyMapField` are gone: between Volto's `Form` and the driver schema there was nothing left for them to do. @ericof
