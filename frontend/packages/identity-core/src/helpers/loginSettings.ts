/**
 * What both frontends' login pages decide the same way.
 *
 * Where each frontend reads a setting from differs -- Volto's
 * `runtimeConfig`, Aurora's registry -- and stays in its add-on. How a value
 * is read, and the query parameter that overrides the sole-provider
 * redirect, are the same in both.
 * @module helpers/loginSettings
 */

/**
 * The query parameter that asks `/login` to show its options anyway.
 *
 * Its presence is the request, whatever its value.
 */
export const CHOOSE_PARAM = 'choose';

/**
 * The login page with its options on screen, whatever the setting says.
 *
 * Where the callback page sends a visitor whose sign-in failed. Plain
 * `/login` would start the same provider again, and a provider that refuses
 * somebody refuses them every time.
 */
export const CHOOSE_LOGIN_PATH = `/login?${CHOOSE_PARAM}=1`;

/**
 * Whether a query string asks for the options rather than the redirect.
 *
 * @param search The location's query string.
 * @returns Whether `choose` is on it.
 */
export function asksToChoose(search: string): boolean {
  return new URLSearchParams(search).has(CHOOSE_PARAM);
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
