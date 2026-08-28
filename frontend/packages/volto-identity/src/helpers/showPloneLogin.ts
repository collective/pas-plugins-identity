/**
 * Whether Plone's own username/password form is offered on the login page.
 * @module helpers/showPloneLogin
 */
import { runtimeConfig } from '@plone/volto/runtime_config';
import config from '@plone/volto/registry';

import { asBoolean } from '../config/settings';

/**
 * The environment variable a deployment answers this with.
 *
 * `RAZZLE_`-prefixed because that is the only prefix Volto carries into
 * `runtimeConfig`.
 */
export const SHOW_PLONE_LOGIN_ENV = 'RAZZLE_IDENTITY_SHOW_PLONE_LOGIN';

/**
 * Decide whether to offer the password form.
 *
 * Read through Volto's `runtimeConfig` rather than `process.env`, which is
 * what makes this a *runtime* answer instead of a property of the image.
 * `process.env.RAZZLE_...`, written out literally, is substituted into the
 * browser bundle by webpack's DefinePlugin while `pnpm build` runs -- so a
 * value supplied to a running container reaches the node process and never
 * the browser. It looks like it works and does nothing, and two sites wanting
 * two answers need two images.
 *
 * `runtimeConfig` avoids that on both sides, which is why it is used instead
 * of reading `window.env` directly:
 *
 * - on the server it enumerates `process.env` and filters to `RAZZLE_*`, with
 *   computed keys DefinePlugin cannot rewrite, so the node process is read as
 *   it actually is;
 * - on the client it reads `window.env`, which the server serialized into the
 *   page while rendering it.
 *
 * Both therefore see the same value, and the server-rendered markup matches
 * what React hydrates. Reading only `window.env` would render the default on
 * the server and the real answer in the browser -- a mismatch, and a flash of
 * the wrong form.
 *
 * The setting is the fallback rather than the source, so a project that ships
 * its own default keeps it and a deployment can still override it.
 *
 * @returns Whether to offer the password form.
 */
export function showPloneLogin(): boolean {
  return asBoolean(
    (runtimeConfig as Record<string, string | undefined>)?.[
      SHOW_PLONE_LOGIN_ENV
    ],
    Boolean(config.settings.identityShowPloneLogin),
  );
}
