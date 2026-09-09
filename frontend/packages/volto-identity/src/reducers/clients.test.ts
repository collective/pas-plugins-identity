import { describe, expect, it } from 'vitest';

import {
  CREATE_CLIENT,
  DELETE_CLIENT,
  LIST_CLIENTS,
  LIST_KEYS,
  ROTATE_CLIENT_SECRET,
} from '../constants/ActionTypes';
import {
  clientCreate,
  clientDelete,
  clientSecretRotate,
  oauthClients,
} from './clients';
import { signingKeys } from './keys';

describe('the OAuth client reducers', () => {
  it('keeps the listing items', () => {
    const state = oauthClients(undefined, {
      type: `${LIST_CLIENTS}_SUCCESS`,
      result: { items: [{ client_id: 'app' }], items_total: 1 },
    });

    expect(state.data).toEqual([{ client_id: 'app' }]);
  });

  it('keeps the whole client on create, because the secret is on it', () => {
    const result = { client_id: 'app', secret: 's3cr3t' };

    const state = clientCreate(undefined, {
      type: `${CREATE_CLIENT}_SUCCESS`,
      result,
    });

    expect(state.data).toEqual(result);
  });

  it('keeps the whole client on rotation, for the same reason', () => {
    const result = { client_id: 'app', secret: 'fresher' };

    const state = clientSecretRotate(undefined, {
      type: `${ROTATE_CLIENT_SECRET}_SUCCESS`,
      result,
    });

    expect(state.data.secret).toBe('fresher');
  });

  it('clears the previous secret while a new request is pending', () => {
    // Otherwise a failed rotation leaves the last secret on screen looking
    // like it succeeded.
    const loaded = clientSecretRotate(undefined, {
      type: `${ROTATE_CLIENT_SECRET}_SUCCESS`,
      result: { client_id: 'app', secret: 'old' },
    });

    const pending = clientSecretRotate(loaded, {
      type: `${ROTATE_CLIENT_SECRET}_PENDING`,
    });

    expect(pending.data).toBeNull();
  });

  it('records a delete without keeping a body', () => {
    const state = clientDelete(undefined, { type: `${DELETE_CLIENT}_SUCCESS` });

    expect(state.data).toBe(true);
    expect(state.loaded).toBe(true);
  });

  it('keeps the ring description', () => {
    const result = { algorithm: 'RS256', items: [], items_total: 0 };

    const state = signingKeys(undefined, {
      type: `${LIST_KEYS}_SUCCESS`,
      result,
    });

    expect(state.data).toEqual(result);
  });

  it('records a failure without pretending it loaded', () => {
    const state = oauthClients(undefined, {
      type: `${LIST_CLIENTS}_FAIL`,
      error: 'nope',
    });

    expect(state.error).toBe('nope');
    expect(state.loaded).toBe(false);
  });
});
