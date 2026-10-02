/**
 * Reading the credential off a callback URL.
 *
 * Kept out of the component so it can be tested as what it is: a pure
 * function over a query string, and the place every refusal is decided.
 *
 * Uses ``URLSearchParams`` rather than a query-string library, which brings
 * the repeated-parameter handling with it: ``getAll`` makes ``?code=a&code=b``
 * visibly two values, and picking one of two credentials an attacker supplied
 * is not a decision this should be making quietly.
 * @module helpers/callback
 */

export type CallbackKind = 'code' | 'magic-link' | 'error' | 'none';

export interface ParsedCallback {
  kind: CallbackKind;
  provider?: string;
  code?: string;
  state?: string;
  token?: string;
  error?: string;
}

/**
 * Return a parameter only when it appears exactly once.
 *
 * @param params The parsed query string.
 * @param name Parameter to read.
 * @returns The value, or ``undefined`` when absent or repeated.
 */
function single(params: URLSearchParams, name: string): string | undefined {
  const values = params.getAll(name);
  return values.length === 1 ? values[0] : undefined;
}

/**
 * Read the credential off a callback URL.
 *
 * @param search The query string, with or without its leading ``?``.
 * @returns What kind of callback this is, and its parts.
 */
export function readCallback(search: string): ParsedCallback {
  const params = new URLSearchParams(search);

  const error = single(params, 'error');
  if (error) {
    // Providers report a refusal by redirecting back with ?error=, not by
    // failing the redirect. Without this the page would sit on "signing you
    // in" forever.
    return { kind: 'error', error };
  }

  const token = single(params, 'magic_link');
  if (token) {
    return { kind: 'magic-link', token };
  }

  const code = single(params, 'code');
  const state = single(params, 'state');
  if (code && state) {
    return {
      kind: 'code',
      code,
      state,
      provider: single(params, 'provider') ?? '',
    };
  }

  return { kind: 'none' };
}
