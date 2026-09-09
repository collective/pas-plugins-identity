import { describe, expect, it } from 'vitest';

import { confirmMagicLink, sendMagicLink } from './magiclink';

describe('magic link', () => {
  it('sends an address', () => {
    const { op, path, data } = sendMagicLink('erico@plone.org').request;

    expect(op).toBe('post');
    expect(path).toBe('/@magic-link');
    expect(data).toEqual({ email: 'erico@plone.org' });
  });

  it('confirms a token', () => {
    const { path, data } = confirmMagicLink('tok').request;

    expect(path).toBe('/@magic-link-confirm');
    expect(data).toEqual({ token: 'tok' });
  });
});
