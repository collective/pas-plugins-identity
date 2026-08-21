import { describe, expect, it } from 'vitest';

import {
  completeCallback,
  confirmMagicLink,
  getMyProfile,
  listLoginProviders,
  sendMagicLink,
  startProviderLogin,
} from './index';

describe('listLoginProviders', () => {
  it('reads the listing', () => {
    expect(listLoginProviders().request).toEqual({
      op: 'get',
      path: '/@login-providers',
    });
  });
});

describe('startProviderLogin', () => {
  it('addresses one provider', () => {
    expect(startProviderLogin('dex').request.path).toBe(
      '/@login-providers/dex',
    );
  });

  it('carries came_from when there is one', () => {
    const { path } = startProviderLogin('dex', '/some/page').request;

    expect(path).toBe('/@login-providers/dex?came_from=%2Fsome%2Fpage');
  });

  it('encodes came_from rather than pasting it in', () => {
    const { path } = startProviderLogin('dex', '/a page?with=query').request;

    // An unencoded value would end the query string early and silently drop
    // the rest of the target.
    expect(path).not.toContain(' ');
    expect(path).toContain('%3Fwith%3Dquery');
  });

  it('omits the parameter entirely when there is nothing to carry', () => {
    expect(startProviderLogin('dex', '').request.path).toBe(
      '/@login-providers/dex',
    );
  });
});

describe('completeCallback', () => {
  it('posts all three parts', () => {
    const { op, path, data } = completeCallback(
      'dex',
      'the-code',
      'the-state',
    ).request;

    expect(op).toBe('post');
    expect(path).toBe('/@identity-callback');
    expect(data).toEqual({
      provider: 'dex',
      code: 'the-code',
      state: 'the-state',
    });
  });
});

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

describe('getMyProfile', () => {
  it('reads the routing endpoint', () => {
    expect(getMyProfile().request).toEqual({
      op: 'get',
      path: '/@my-profile',
    });
  });
});
