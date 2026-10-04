import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import config from '@plone/registry';

import {
  applicationsAvailable,
  FEATURE_TTL,
  featureTtl,
  forgetFeatures,
} from './features';

const BACKEND = 'http://localhost:8080/Plone';
const REQUEST = new Request('http://localhost:3000/');

/**
 * Answer `@oauth-grants` with a status.
 *
 * @param status The status.
 * @returns The stand-in for `fetch`.
 */
function backendAnswers(status: number) {
  const fetch = vi.fn(async () => new Response('{}', { status }));
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

describe('applicationsAvailable', () => {
  beforeEach(() => {
    config.settings.apiPath = BACKEND;
    forgetFeatures();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('is true where the authorization server answers', async () => {
    backendAnswers(200);

    expect(await applicationsAvailable(REQUEST, 't', BACKEND)).toBe(true);
  });

  it('is false where it is not installed', async () => {
    backendAnswers(404);

    expect(await applicationsAvailable(REQUEST, 't', BACKEND)).toBe(false);
  });

  it('asks once per backend for a while, not on every page', async () => {
    const fetch = backendAnswers(200);

    await applicationsAvailable(REQUEST, 't', BACKEND, 0);
    await applicationsAvailable(REQUEST, 't', BACKEND, FEATURE_TTL - 1);
    expect(fetch).toHaveBeenCalledTimes(1);

    await applicationsAvailable(REQUEST, 't', BACKEND, FEATURE_TTL);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('keeps nothing when told to', async () => {
    const fetch = backendAnswers(200);

    await applicationsAvailable(REQUEST, 't', BACKEND, 0, 0);
    await applicationsAvailable(REQUEST, 't', BACKEND, 0, 0);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('takes how long to keep it from the environment', () => {
    vi.stubEnv('IDENTITY_FEATURE_TTL', '0');
    expect(featureTtl()).toBe(0);
    vi.stubEnv('IDENTITY_FEATURE_TTL', '');
    expect(featureTtl()).toBe(FEATURE_TTL);
    vi.unstubAllEnvs();
  });

  it('does not keep an answer about a session rather than the site', async () => {
    const fetch = backendAnswers(401);

    expect(await applicationsAvailable(REQUEST, 't', BACKEND, 0)).toBe(false);
    await applicationsAvailable(REQUEST, 't', BACKEND, 1);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
