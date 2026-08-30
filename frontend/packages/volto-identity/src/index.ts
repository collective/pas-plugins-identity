import type { ConfigType } from '@plone/registry';
import installReducers from './config/reducers';
import installRoutes from './config/routes';
import installSettings from './config/settings';
import installMenu from './config/menu';
import installViews from './config/views';
import installWidgets from './config/widgets';

import './styles.css';

function applyConfig(config: ConfigType) {
  installSettings(config);
  installReducers(config);
  installRoutes(config);
  installMenu(config);
  installViews(config);
  installWidgets(config);

  return config;
}

export default applyConfig;
