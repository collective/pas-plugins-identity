import { describe, expect, it } from 'vitest';

import {
  createClient,
  deleteClient,
  listClients,
  rotateClientSecret,
  updateClient,
} from './clients';

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
