import { describe, expect, it } from 'vitest';

import { EMAIL_DRIVER, linkable, splitLinkable } from './identities';
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

describe('splitLinkable', () => {
  const email: LoginProvider = {
    '@id': '/@login-providers/email',
    id: 'email',
    title: 'Email',
    driver: EMAIL_DRIVER,
  };

  it('keeps redirect providers as buttons', () => {
    const result = splitLinkable([provider('dex'), email]);

    expect(result.redirect.map((p) => p.id)).toEqual(['dex']);
  });

  it('pulls the email provider out', () => {
    // Rendering it as a button posted a link request for a provider with no
    // authorize URL, and the backend refused it.
    const result = splitLinkable([provider('dex'), email]);

    expect(result.email?.id).toBe('email');
  });

  it('answers no email provider when the site offers none', () => {
    const result = splitLinkable([provider('dex')]);

    expect(result.email).toBeNull();
  });

  it('finds the email provider whatever it is called', () => {
    // The id is the operator's; the driver is what decides how it is
    // offered.
    const result = splitLinkable([{ ...email, id: 'mailbox' }]);

    expect(result.email?.id).toBe('mailbox');
    expect(result.redirect).toEqual([]);
  });
});
