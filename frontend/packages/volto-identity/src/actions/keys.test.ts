import { describe, expect, it } from 'vitest';

import { listKeys, rotateKey } from './keys';

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
