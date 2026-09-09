import { describe, expect, it } from 'vitest';

import { listIdentities, startLinking } from './identities';

describe('listIdentities', () => {
  it('reads the listing', () => {
    expect(listIdentities().request.path).toBe('/@identities');
  });

  it('can ask for the providers alongside, in one request', () => {
    expect(listIdentities(true).request.path).toBe(
      '/@identities?expand=login-providers',
    );
  });
});

describe('startLinking', () => {
  it('names the provider to link', () => {
    expect(startLinking('github', '/identities').request.data).toEqual({
      provider: 'github',
      came_from: '/identities',
    });
  });

  it('sends no address for a redirect provider', () => {
    // The backend takes none, and an empty one would be a malformed request
    // rather than an omitted field.
    expect(startLinking('github').request.data).not.toHaveProperty('email');
  });

  it('carries the address for the email provider', () => {
    expect(
      startLinking('email', '/identities', 'erico@plone.org').request.data,
    ).toEqual({
      provider: 'email',
      came_from: '/identities',
      email: 'erico@plone.org',
    });
  });
});
