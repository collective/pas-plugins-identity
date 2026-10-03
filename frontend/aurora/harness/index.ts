import type { ConfigType } from '@plone/registry';

/**
 * Leave the configuration as it is.
 *
 * This add-on exists for its `vite.extend.js` alone; Aurora requires every
 * add-on to export a configuration function all the same.
 *
 * @param config The registry.
 * @returns The same registry.
 */
export default function install(config: ConfigType) {
  return config;
}
