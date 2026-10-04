/**
 * The login page's two switches, as Aurora reads them.
 *
 * The same two the Volto add-on has, with the same defaults. Aurora reads
 * them where the login page's loader runs, on the server, so the environment
 * is read at run time and no build step bakes a value into the bundle: a
 * deployment answers them with `IDENTITY_SHOW_PLONE_LOGIN` and
 * `IDENTITY_REDIRECT_TO_SOLE_PROVIDER`, and
 * `config.settings.identity` is the fallback.
 * @module lib/settings
 */
import { asBoolean } from '@plone-collective/identity-core';

/** The environment variable that offers Plone's own password form. */
export const SHOW_PLONE_LOGIN_ENV = 'IDENTITY_SHOW_PLONE_LOGIN';

/** The environment variable that starts a sole provider straight away. */
export const REDIRECT_TO_SOLE_PROVIDER_ENV =
  'IDENTITY_REDIRECT_TO_SOLE_PROVIDER';

/** `config.settings.identity`. */
export interface IdentitySettings {
  /**
   * Whether Plone's own password form is offered beside the providers.
   *
   * Off by default: a site installing this add-on has external providers,
   * and a password form beside them invites a second way into the same
   * account. A site with no provider configured shows it regardless.
   */
  showPloneLogin: boolean;
  /** Whether one provider, when it is the only way in, is started at once. */
  redirectToSoleProvider: boolean;
}

/** What the add-on installs into `config.settings.identity`. */
export const DEFAULT_SETTINGS: IdentitySettings = {
  showPloneLogin: false,
  redirectToSoleProvider: true,
};

/**
 * Decide both switches.
 *
 * @param configured `config.settings.identity`, the fallback.
 * @param env The environment, which wins.
 * @returns The decision.
 */
export function loginSettings(
  configured: Partial<IdentitySettings> | undefined,
  env: Record<string, string | undefined>,
): IdentitySettings {
  const fallback = { ...DEFAULT_SETTINGS, ...configured };
  return {
    showPloneLogin: asBoolean(
      env[SHOW_PLONE_LOGIN_ENV],
      fallback.showPloneLogin,
    ),
    redirectToSoleProvider: asBoolean(
      env[REDIRECT_TO_SOLE_PROVIDER_ENV],
      fallback.redirectToSoleProvider,
    ),
  };
}
