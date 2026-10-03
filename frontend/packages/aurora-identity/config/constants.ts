/**
 * Names the server configuration and the components share.
 *
 * Its own module so a component can import them without pulling
 * `config/server.ts` into the browser bundle.
 * @module config/constants
 */

/** The root loader data key the login page's providers are under. */
export const PROVIDERS_KEY = 'identityLoginProviders';
