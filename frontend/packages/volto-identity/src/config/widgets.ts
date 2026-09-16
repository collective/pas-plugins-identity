import type { ConfigType } from '@plone/registry';
import OrderedObjectListWidget from '../components/Widgets/OrderedObjectListWidget/OrderedObjectListWidget';
import OrderedStringListWidget from '../components/Widgets/OrderedStringListWidget/OrderedStringListWidget';
import ProviderIconWidget from '../components/Widgets/ProviderIconWidget';

/**
 * The widgets this add-on supplies, and who decides which field uses them.
 *
 * A widget is a component, so it can only live in the frontend. *Which* widget
 * a field uses is a different question, and that one belongs to the backend:
 * every field this add-on renders says so itself, through
 * `directives.widget(..., frontendOptions={"widget": ...})`, and Volto looks
 * the name up in this map. So the provider form asks for `color_picker` and
 * `token` and gets Volto's own, and asks for `provider_icon` and gets this
 * package's.
 *
 * That split is what the schema rewrite was about (Érico, 2026-08-29): the
 * backend decides what a field is and how it should be edited, and the
 * frontend supplies the component when it has one Volto does not.
 *
 * **Only names this package owns.** A field belonging to another add-on keeps
 * that add-on's widget: registering somebody else's name here would replace
 * their component on their own field, decided by nothing more than the order
 * the add-ons happen to be listed in.
 */
export default function install(config: ConfigType) {
  config.widgets.widget = {
    ...config.widgets.widget,
    provider_icon: ProviderIconWidget,
    identity_string_list: OrderedStringListWidget,
    identity_object_list: OrderedObjectListWidget,
  };

  return config;
}
