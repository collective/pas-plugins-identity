import type { ConfigType } from '@plone/registry';

declare module '@plone/types' {
  export interface SettingsConfig {
    /** Whether Plone's own username/password form is offered as well. */
    identityShowPloneLogin: boolean;
  }
}

/**
 * Read a boolean out of the environment.
 *
 * Only the words are accepted, and anything unset falls back to the default.
 * Deliberately not `Boolean(value)`: that reads the string `"false"` as true,
 * which turns an operator switching the password form *off* into a site that
 * still shows it.
 *
 * @param value The raw environment value.
 * @param fallback What an unset variable means.
 * @returns The decision.
 */
export function asBoolean(
  value: string | undefined,
  fallback: boolean,
): boolean {
  if (value === undefined || value === '') {
    return fallback;
  }
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase());
}

export default function install(config: ConfigType) {
  // Off by default: a site installing this add-on has external providers,
  // and leaving the password form up next to them invites people to create a
  // second way into the same account.
  //
  // An identity provider built on this package is the case that wants it on:
  // its users *are* local, and it is the site people sign in to in order to
  // sign in elsewhere. That is a deployment fact rather than a code one, so
  // it is an environment variable and not a different bundle.
  //
  // `RAZZLE_`-prefixed because that is the only prefix Volto's build passes
  // through to the browser bundle, and written out literally because the
  // build substitutes the exact text `process.env.RAZZLE_...`: read through a
  // variable it is `undefined` on the client, and the setting would then
  // differ between the server-rendered page and the one React takes over.
  //
  // It is read at **build** time. Razzle substitutes these with webpack's
  // DefinePlugin while the bundle is built, so a value supplied to the
  // running container reaches the node process and never the browser --
  // which looks like it works and does nothing. In Docker it is a build
  // argument; see `frontend/Dockerfile`.
  config.settings.identityShowPloneLogin = asBoolean(
    process.env.RAZZLE_IDENTITY_SHOW_PLONE_LOGIN,
    false,
  );
  return config;
}
