/**
 * The add-on's server-only configuration.
 *
 * Aurora loads `config/server.ts` from every add-on into the server bundle
 * alone, which is where a `rootLoaderData` utility belongs.
 * @module config/server
 */
import type { ConfigType } from '@plone/registry';
import { endpoints } from '@plone-collective/identity-core';
import type { LoginProvider } from '@plone-collective/identity-core';

import { backendUrl } from '../lib/backend';
import { PROVIDERS_KEY } from './constants';

/**
 * Whether a request is for the login page.
 *
 * By the URL rather than the root loader's `path`: the login route has no
 * content splat, so its `path` is `/` like the site root's.
 *
 * @param request The request.
 * @returns Whether it asks for `/login`.
 */
function isLoginPage(request: Request): boolean {
  return new URL(request.url).pathname.replace(/\/+$/, '') === '/login';
}

export default function install(config: ConfigType) {
  config.registerUtility({
    name: 'IdentityLoginProviders',
    type: 'rootLoaderData',
    method: async ({ request }: { request: Request }) => {
      // Every page renders the root loader; only the login page offers the
      // providers, so only it pays for asking which there are.
      if (!isLoginPage(request)) {
        return { status: 200, data: {} };
      }
      try {
        const answer = await fetch(
          backendUrl(
            config.settings.apiPath,
            request.url,
            endpoints.loginProviders(),
          ),
          { headers: { Accept: 'application/json' } },
        );
        if (!answer.ok) {
          return { status: answer.status, data: { [PROVIDERS_KEY]: [] } };
        }
        const listing = (await answer.json()) as { items?: LoginProvider[] };
        return {
          status: 200,
          data: { [PROVIDERS_KEY]: listing.items ?? [] },
        };
      } catch {
        // The login page still has the password form; an unreachable
        // backend costs it the buttons, not the page.
        return { status: 502, data: { [PROVIDERS_KEY]: [] } };
      }
    },
  });
  return config;
}
