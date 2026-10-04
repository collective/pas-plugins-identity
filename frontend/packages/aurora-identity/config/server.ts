/**
 * The add-on's server-only configuration.
 *
 * Aurora loads `config/server.ts` from every add-on into the server bundle
 * alone, which is where a `rootLoaderData` utility belongs.
 * @module config/server
 */
import type { ConfigType } from '@plone/registry';
import { getAuthFromRequest } from '@plone/react-router';
import { endpoints } from '@plone-collective/identity-core';

import { callBackend } from '../lib/api';
import { APPLICATIONS_KEY } from '../lib/paths';
import { applicationsAvailable } from '../lib/features';
import { PROFILE_KEY } from '../lib/gate';

export default function install(config: ConfigType) {
  // The signed-in user's `@my-profile`, for the profile gate, on every page.
  //
  // One request per signed-in page. The Volto add-on gets the same answer
  // for free, as an expansion of the content request it was making anyway;
  // Aurora's content request expands a fixed list an add-on cannot add to.
  config.registerUtility({
    name: 'IdentityProfileGate',
    type: 'rootLoaderData',
    method: async ({ request }: { request: Request }) => {
      const token = await getAuthFromRequest(request);
      if (!token) {
        return { status: 200, data: {} };
      }
      try {
        const answer = await callBackend(request, endpoints.myProfile(), {
          token,
        });
        if (!answer.ok) {
          // A backend that cannot answer must not make the site
          // unreachable: without an answer, the gate lets everybody through.
          return { status: answer.status, data: {} };
        }
        return { status: 200, data: { [PROFILE_KEY]: await answer.json() } };
      } catch {
        return { status: 502, data: {} };
      }
    },
  });

  // Whether to offer the applications page among the user's tools: only
  // where the authorization server is installed. Asked once per backend for
  // a few minutes, not on every page; see `lib/features`.
  config.registerUtility({
    name: 'IdentityApplications',
    type: 'rootLoaderData',
    method: async ({ request }: { request: Request }) => {
      const token = await getAuthFromRequest(request);
      if (!token) {
        return { status: 200, data: {} };
      }
      const available = await applicationsAvailable(
        request,
        token,
        config.settings.apiPath,
      );
      return { status: 200, data: { [APPLICATIONS_KEY]: available } };
    },
  });
  return config;
}
