import type { ConfigType } from '@plone/registry';
import UserProfileLoader from '../components/UserMenu/UserProfileLoader';

export default function install(config: ConfigType) {
  // The menu's entries are not registered here: they are the backend's
  // `personal_tools` actions, which this package's profile declares.
  //
  // `appExtras` with an empty `match` is mounted on every route: Volto hands
  // it to `matchPath`, and an empty path matches everything.
  config.settings.appExtras = [
    ...(config.settings.appExtras ?? []),
    // Renders nothing; it is here to keep the signed-in user in the store
    // for the menu's header, which Volto only loads when the menu opens.
    { match: '', component: UserProfileLoader, props: {} },
  ];
  return config;
}
