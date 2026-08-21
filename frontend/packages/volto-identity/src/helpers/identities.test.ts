import { describe, expect, it } from 'vitest';

import { linkable } from './identities';
import type { Identity, LoginProvider } from '../types';

const provider = (id: string): LoginProvider => ({
  '@id': `/@login-providers/${id}`,
  id,
  title: id,
  driver: 'oidc-generic',
});

const identity = (provider: string): Identity => ({
  '@id': `/@identities/${provider}/s`,
  provider,
  subject: 's',
  title: provider,
  created: '2026-08-21T10:00:00+00:00',
  last_login: null,
  can_unlink: true,
});

describe('linkable', () => {
  it('offers providers the user has not linked', () => {
    const result = linkable(
      [provider('dex'), provider('github')],
      [identity('dex')],
    );

    expect(result.map((p) => p.id)).toEqual(['github']);
  });

  it('offers everything when nothing is linked', () => {
    const result = linkable([provider('dex')], []);

    expect(result.map((p) => p.id)).toEqual(['dex']);
  });

  it('offers nothing when everything is linked', () => {
    // Offering a provider they already use would start a flow that ends in a
    // collision, which is a confusing way to learn you are already signed up.
    const result = linkable([provider('dex')], [identity('dex')]);

    expect(result).toEqual([]);
  });

  it('ignores identities for providers the site no longer offers', () => {
    const result = linkable([provider('dex')], [identity('retired')]);

    expect(result.map((p) => p.id)).toEqual(['dex']);
  });
});
