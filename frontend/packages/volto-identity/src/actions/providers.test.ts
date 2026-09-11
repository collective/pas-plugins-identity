import { describe, expect, it } from 'vitest';

import { REORDER_PROVIDERS } from '../constants/ActionTypes';
import { reorderProviders } from './providers';

describe('the provider actions', () => {
  it('reorders every provider in one request', () => {
    // One request for the whole list, so a reorder is never half applied.
    const action = reorderProviders(['github', 'dex']);

    expect(action.type).toBe(REORDER_PROVIDERS);
    expect(action.request).toEqual({
      op: 'patch',
      path: '/@identity-providers',
      data: { order: ['github', 'dex'] },
    });
  });
});
