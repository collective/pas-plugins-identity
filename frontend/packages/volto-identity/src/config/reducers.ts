import type { ConfigType } from '@plone/registry';
import reducers from '../reducers';

export default function install(config: ConfigType) {
  config.addonReducers = { ...config.addonReducers, ...reducers };
  return config;
}
