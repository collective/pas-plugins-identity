/**
 * What the Volto and Aurora frontends of `pas.plugins.identity` share.
 *
 * Nothing in this package may import a frontend framework: not Volto, not
 * Aurora, not Redux, not a router, not an i18n library, and not React. Each
 * frontend's add-on adapts these pieces to its own framework.
 * @module identity-core
 */

export * from './constants/vocabularies';
export * from './endpoints';
export * from './helpers/avatar';
export * from './helpers/callback';
export * from './helpers/download';
export * from './helpers/firstLogin';
export * from './helpers/groupmap';
export * from './helpers/identities';
export * from './helpers/navigate';
export * from './helpers/orderedList';
export * from './helpers/profileGate';
export * from './helpers/profileSource';
export * from './helpers/propertymap';
export * from './helpers/providerOrder';
export * from './helpers/returnUrl';
export * from './helpers/rowmap';
export * from './helpers/token';
export * from './helpers/welcome';
export * from './types';

/**
 * Leave the configuration as it is.
 *
 * Volto transpiles only the packages registered as add-ons, and this package
 * ships TypeScript source, so `volto-identity` registers it as one. Volto
 * then requires every add-on to default-export a configuration function.
 * Aurora does not register it, and never calls this.
 *
 * @param config The frontend's configuration registry.
 * @returns The same configuration, unchanged.
 */
export default function applyConfig<T>(config: T): T {
  return config;
}
