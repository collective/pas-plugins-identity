import { describe, expect, it } from 'vitest';

import {
  completeCallback,
  confirmMagicLink,
  createClient,
  deleteClient,
  getMyProfile,
  listClients,
  listKeys,
  listLoginProviders,
  rotateClientSecret,
  rotateKey,
  sendMagicLink,
  startProviderLogin,
  updateClient,
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

describe('the OAuth client registry', () => {
  it('lists clients', () => {
    expect(listClients().request).toEqual({
      op: 'get',
      path: '/@identity-clients',
    });
  });

  it('registers one', () => {
    const { op, path, data } = createClient({ client_id: 'app' }).request;

    expect(op).toBe('post');
    expect(path).toBe('/@identity-clients');
    expect(data).toEqual({ client_id: 'app' });
  });

  it('amends one', () => {
    const { op, path, data } = updateClient('app', { enabled: false }).request;

    expect(op).toBe('patch');
    expect(path).toBe('/@identity-clients/app');
    expect(data).toEqual({ enabled: false });
  });

  it('unregisters one', () => {
    const { op, path } = deleteClient('app').request;

    expect(op).toBe('del');
    expect(path).toBe('/@identity-clients/app');
  });

  it('rotates a secret', () => {
    const { op, path } = rotateClientSecret('app').request;

    expect(op).toBe('post');
    expect(path).toBe('/@identity-clients/app/rotate-secret');
  });

  it('escapes a client id with a slash in it', () => {
    // A client id is operator-supplied and is not validated as a URL
    // segment, so an unescaped one would silently address a different path.
    expect(deleteClient('a/b').request.path).toBe('/@identity-clients/a%2Fb');
  });
});

describe('the signing key ring', () => {
  it('reads the ring', () => {
    expect(listKeys().request).toEqual({
      op: 'get',
      path: '/@identity-keys',
    });
  });

  it('rotates the key', () => {
    const { op, path } = rotateKey().request;

    expect(op).toBe('post');
    expect(path).toBe('/@identity-keys/rotate');
  });
});
