import type { ConfigType } from '@plone/registry';
import IdentitiesMenuItem from '../components/UserMenu/IdentitiesMenuItem';
import ProfileMenuItem from '../components/UserMenu/ProfileMenuItem';
import UserProfileLoader from '../components/UserMenu/UserProfileLoader';

export default function install(config: ConfigType) {
  // A `Plug` renders nothing itself -- it registers with the pluggable and
  // returns null -- so it has to be mounted somewhere that is always rendered.
  // `appExtras` with an empty `match` is that place: Volto hands it to
  // `matchPath`, and an empty path matches every route. The entry only becomes
  // visible when Volto renders the user menu, which is authenticated-only.
  config.settings.appExtras = [
    ...(config.settings.appExtras ?? []),
    // Renders nothing; it is here to keep the signed-in user in the store
    // for everything below, which Volto only loads when the menu opens.
    { match: '', component: UserProfileLoader, props: {} },
    { match: '', component: IdentitiesMenuItem, props: {} },
    { match: '', component: ProfileMenuItem, props: {} },
  ];
  return config;
}
