/**
 * Calling the backend from a route's loader or action.
 *
 * Through the virtual-host URL `lib/backend` builds, so every URL the
 * backend answers with names Aurora, and as the signed-in user when there is
 * one.
 * @module lib/api
 */
import config from '@plone/registry';

import { backendUrl } from './backend';

interface CallOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  /** Sent as JSON. */
  body?: object;
  /** The user's session token, sent as a bearer token. */
  token?: string | null;
  /** More headers, such as the flow cookie. */
  headers?: Record<string, string>;
}

/**
 * Call a backend service as the public site.
 *
 * @param request The request the browser made to Aurora.
 * @param path The service path, from `endpoints`.
 * @param options The method, body and session.
 * @returns The backend's answer.
 */
export function callBackend(
  request: Request,
  path: string,
  { method = 'GET', body, token, headers = {} }: CallOptions = {},
): Promise<Response> {
  return fetch(backendUrl(config.settings.apiPath, request.url, path), {
    method,
    headers: {
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}
