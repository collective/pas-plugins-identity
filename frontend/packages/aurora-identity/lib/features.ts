/**
 * Whether the backend runs the authorization server.
 *
 * `@oauth-grants`, and with it the applications page, is published by the
 * `[server]` layer alone, and nothing in any payload says whether a site has
 * it: core may not depend on that layer. So the endpoint is asked, as the
 * Volto add-on asks it before showing the applications entry.
 *
 * It is a property of the site, not of the user, so the answer is kept for a
 * few minutes per backend rather than asked on every page.
 * @module lib/features
 */
import { endpoints } from '@plone-collective/identity-core';

import { callBackend } from './api';

/** How long an answer is kept by default, in milliseconds. */
export const FEATURE_TTL = 5 * 60 * 1000;

/**
 * How long an answer is kept, in milliseconds.
 *
 * `IDENTITY_FEATURE_TTL`, in seconds, overrides the default: the acceptance
 * tests install the authorization server half way through a run, and set it
 * to 0 so the next page sees it.
 *
 * @returns The time to keep an answer for.
 */
export function featureTtl(): number {
  const seconds = Number(process.env.IDENTITY_FEATURE_TTL);
  return Number.isFinite(seconds) && process.env.IDENTITY_FEATURE_TTL !== ''
    ? seconds * 1000
    : FEATURE_TTL;
}

const answers = new Map<string, { available: boolean; at: number }>();

/**
 * Whether the applications page has anything to show on this site.
 *
 * @param request The browser's request.
 * @param token The signed-in user's session: the endpoint answers nobody
 *   else.
 * @param backend The backend the answer is kept for.
 * @param now The time, for the tests.
 * @param ttl How long an answer is kept.
 * @returns Whether `@oauth-grants` answered.
 */
export async function applicationsAvailable(
  request: Request,
  token: string,
  backend: string,
  now = Date.now(),
  ttl = featureTtl(),
): Promise<boolean> {
  const kept = answers.get(backend);
  if (kept && now - kept.at < ttl) {
    return kept.available;
  }
  let available = false;
  try {
    const answer = await callBackend(request, endpoints.grants(), { token });
    // A 401 says nothing about the site, only about this session: not kept.
    if (answer.status === 401) {
      return false;
    }
    available = answer.ok;
  } catch {
    return false;
  }
  answers.set(backend, { available, at: now });
  return available;
}

/** Forget every answer, for the tests. */
export function forgetFeatures(): void {
  answers.clear();
}
