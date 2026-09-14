import type { ConfigType } from '@plone/registry';
import OrderedObjectListWidget, {
  SocialLinksWidget,
} from '../components/Widgets/OrderedObjectListWidget/OrderedObjectListWidget';
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
 * **One name here is somebody else's.** `social_media_object_list` is what
 * `plonegovbr.socialmedia` asks for on `social_links`, a field this package
 * does not own and so cannot point at `identity_object_list`. Registering the
 * same name replaces `volto-social-media`'s widget -- but add-on configuration
 * is applied in the order the add-ons are listed, so it only does that when
 * this add-on comes after `volto-social-media`.
 */
export default function install(config: ConfigType) {
  config.widgets.widget = {
    ...config.widgets.widget,
    provider_icon: ProviderIconWidget,
    identity_string_list: OrderedStringListWidget,
    identity_object_list: OrderedObjectListWidget,
    social_media_object_list: SocialLinksWidget,
  };

  return config;
}
