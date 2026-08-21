import type { ConfigType } from '@plone/registry';
import installReducers from './config/reducers';
import installRoutes from './config/routes';
import installSettings from './config/settings';

function applyConfig(config: ConfigType) {
  installSettings(config);
  installReducers(config);
  installRoutes(config);

  return config;
}

export default applyConfig;
