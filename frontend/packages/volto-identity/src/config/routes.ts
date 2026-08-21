import type { ConfigType } from '@plone/registry';
import Callback from '../components/Callback/Callback';
import Login from '../components/Login/Login';

/** The frontend route the provider redirects back to. */
export const CALLBACK_PATH = '/login-identity';

export default function install(config: ConfigType) {
  config.settings.nonContentRoutes = [
    ...(config.settings.nonContentRoutes ?? []),
    new RegExp(`^${CALLBACK_PATH}$`),
  ];
  config.addonRoutes = [
    ...(config.addonRoutes ?? []),
    { path: CALLBACK_PATH, exact: true, component: Callback },
    { path: '/login', exact: true, component: Login },
    { path: '/**/login', exact: true, component: Login },
  ];
  return config;
}
