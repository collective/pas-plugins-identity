import type { ConfigType } from '@plone/registry';
import appsSVG from '@plone/volto/icons/apps.svg';
import worldSVG from '@plone/volto/icons/world.svg';
import Applications from '../components/Applications/Applications';
import Callback from '../components/Callback/Callback';
import Consent from '../components/Consent/Consent';
import FirstLogin from '../components/FirstLogin/FirstLogin';
import ClientsControlPanel from '../components/ControlPanel/ClientsControlPanel';
import ProvidersControlPanel from '../components/ControlPanel/ProvidersControlPanel';
import Identities from '../components/Identities/Identities';
import Login from '../components/Login/Login';
import VoltoLogin from '@plone/volto/components/theme/Login/Login';

/** The frontend route the provider redirects back to. */
export const CALLBACK_PATH = '/login-identity';

/** Where a just-signed-in user is routed based on their Profile state. */
export const FIRST_LOGIN_PATH = '/first-login';

/** Where a signed-in user manages their own sign-in methods. */
export const IDENTITIES_PATH = '/identities';

/**
 * Where a signed-in user sees the applications they have authorized.
 *
 * The other direction from `IDENTITIES_PATH`: that page is the providers
 * they sign in *with*, this one the applications they signed in *to*. Only
 * a site running the `[server]` layer has any, and only that layer publishes
 * the endpoint behind it.
 */
export const APPLICATIONS_PATH = '/applications';

/**
 * Where a user is asked whether they agree to an authorization request.
 *
 * Only reached on a site running the `[server]` layer, and only when that
 * layer's `server_consent_url` names it: the authorization endpoint renders
 * a standalone page of its own otherwise. The route exists regardless, since
 * a frontend cannot be configured as the consent screen before it has one.
 */
export const CONSENT_PATH = '/oauth-consent';

/**
 * Where Volto's own login form stays reachable.
 *
 * This add-on takes over `/login` entirely, and its Login already carries a
 * password form beside the provider list -- so this is not the way to sign in
 * with a password. It is the way in when that page cannot be rendered at all:
 * a provider list that fails to load, a misconfigured add-on, a JavaScript
 * error in a component this package owns. Every one of those locks out the
 * administrator who would go and fix it, and none of them are reachable
 * through a page this package draws.
 *
 * The name is `volto-authomatic`'s, which ships the same escape at
 * `/fallback_login` and `/failsafe_login`. A site migrating from it keeps the
 * URL its operators already know.
 */
export const FALLBACK_LOGIN_PATH = '/fallback_login';

/** Where a Manager configures providers. */
export const CONTROLPANEL_PATH = '/controlpanel/identity-providers';

/** Where a Manager configures the OAuth clients this site issues tokens to. */
export const CLIENTS_CONTROLPANEL_PATH = '/controlpanel/identity-clients';

export default function install(config: ConfigType) {
  config.settings.nonContentRoutes = [
    ...(config.settings.nonContentRoutes ?? []),
    new RegExp(`^${CALLBACK_PATH}$`),
    new RegExp(`^${FIRST_LOGIN_PATH}$`),
    new RegExp(`^${IDENTITIES_PATH}$`),
    new RegExp(`^${CONSENT_PATH}$`),
    new RegExp(`^${APPLICATIONS_PATH}$`),
    // Not covered by Volto's own `/login` entry: `nonContentRoutes`
    // strings are tested as unanchored regexes, and `/login` does not
    // occur in `/fallback_login`.
    new RegExp(`^${FALLBACK_LOGIN_PATH}$`),
  ];
  config.addonRoutes = [
    ...(config.addonRoutes ?? []),
    { path: CALLBACK_PATH, exact: true, component: Callback },
    { path: FIRST_LOGIN_PATH, exact: true, component: FirstLogin },
    { path: FALLBACK_LOGIN_PATH, exact: true, component: VoltoLogin },
    { path: '/login', exact: true, component: Login },
    { path: '/**/login', exact: true, component: Login },
    { path: IDENTITIES_PATH, exact: true, component: Identities },
    { path: CONSENT_PATH, exact: true, component: Consent },
    { path: APPLICATIONS_PATH, exact: true, component: Applications },
    { path: CONTROLPANEL_PATH, exact: true, component: ProvidersControlPanel },
    {
      path: CLIENTS_CONTROLPANEL_PATH,
      exact: true,
      component: ClientsControlPanel,
    },
  ];

  // Keyed by configlet id, which is the last segment of each panel's route
  // and what the backend's `controlpanel.xml` calls it. Without an entry
  // Volto draws its generic placeholder, and a control-panel listing where
  // this add-on's two panels are the only unlabelled tiles reads as two
  // things that did not finish installing.
  //
  // A globe for the providers, because every one of them is somewhere else;
  // the apps grid for the clients, because that panel is a list of
  // applications this site issues tokens to. Both are Volto's own icons
  // rather than anything drawn here: a control panel that looks like the
  // control panels beside it is the whole point.
  config.settings.controlPanelsIcons = {
    ...config.settings.controlPanelsIcons,
    'identity-providers': worldSVG,
    'identity-clients': appsSVG,
  };

  return config;
}
