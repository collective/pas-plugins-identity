import type { ConfigType } from '@plone/registry';
import Callback from '../components/Callback/Callback';
import FirstLogin from '../components/FirstLogin/FirstLogin';
import ClientsControlPanel from '../components/ControlPanel/ClientsControlPanel';
import ProvidersControlPanel from '../components/ControlPanel/ProvidersControlPanel';
import Identities from '../components/Identities/Identities';
import Login from '../components/Login/Login';

/** The frontend route the provider redirects back to. */
export const CALLBACK_PATH = '/login-identity';

/** Where a just-signed-in user is routed based on their Profile state. */
export const FIRST_LOGIN_PATH = '/first-login';

/** Where a signed-in user manages their own sign-in methods. */
export const IDENTITIES_PATH = '/identities';

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
  ];
  config.addonRoutes = [
    ...(config.addonRoutes ?? []),
    { path: CALLBACK_PATH, exact: true, component: Callback },
    { path: FIRST_LOGIN_PATH, exact: true, component: FirstLogin },
    { path: '/login', exact: true, component: Login },
    { path: '/**/login', exact: true, component: Login },
    { path: IDENTITIES_PATH, exact: true, component: Identities },
    { path: CONTROLPANEL_PATH, exact: true, component: ProvidersControlPanel },
    {
      path: CLIENTS_CONTROLPANEL_PATH,
      exact: true,
      component: ClientsControlPanel,
    },
  ];
  return config;
}
