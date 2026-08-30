import type { ConfigType } from '@plone/registry';
import ProviderIconWidget from '../components/Widgets/ProviderIconWidget';

/**
 * The one widget this add-on supplies, and the reason it supplies only one.
 *
 * A widget is a component, so it can only live in the frontend. *Which* widget
 * a field uses is a different question, and that one belongs to the backend:
 * every field this add-on renders says so itself, through
 * `directives.widget(..., frontendOptions={"widget": ...})`, and Volto looks
 * the name up in this map. So the provider form asks for `color_picker` and
 * `token` and gets Volto's own, and asks for `provider_icon` and gets this.
 *
 * That split is what the schema rewrite was about (Érico, 2026-08-29): the
 * backend decides what a field is and how it should be edited, and the
 * frontend supplies the component when it has one Volto does not.
 */
export default function install(config: ConfigType) {
  config.widgets.widget = {
    ...config.widgets.widget,
    provider_icon: ProviderIconWidget,
  };

  return config;
}
