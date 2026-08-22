import type { ConfigType } from '@plone/registry';
import IdentitiesMenuItem from '../components/UserMenu/IdentitiesMenuItem';

export default function install(config: ConfigType) {
  // A `Plug` renders nothing itself -- it registers with the pluggable and
  // returns null -- so it has to be mounted somewhere that is always rendered.
  // `appExtras` with an empty `match` is that place: Volto hands it to
  // `matchPath`, and an empty path matches every route. The entry only becomes
  // visible when Volto renders the user menu, which is authenticated-only.
  config.settings.appExtras = [
    ...(config.settings.appExtras ?? []),
    { match: '', component: IdentitiesMenuItem, props: {} },
  ];
  return config;
}
