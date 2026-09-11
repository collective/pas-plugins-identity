import { describe, expect, it } from 'vitest';

import { REORDER_PROVIDERS } from '../constants/ActionTypes';
import { providerReorder } from './providers';

describe('the provider reducers', () => {
  it('records that a reorder was stored', () => {
    // The backend answers a reorder with no content, so there is nothing to
    // keep but the fact that it succeeded.
    const state = providerReorder(undefined, {
      type: `${REORDER_PROVIDERS}_SUCCESS`,
    });

    expect(state.data).toBe(true);
  });
});
