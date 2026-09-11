import { describe, expect, it } from 'vitest';

import { LIST_PROVIDERS, REORDER_PROVIDERS } from '../constants/ActionTypes';
import { providerReorder, providersExportable } from './providers';

describe('the provider reducers', () => {
  it('records that a reorder was stored', () => {
    // The backend answers a reorder with no content, so there is nothing to
    // keep but the fact that it succeeded.
    const state = providerReorder(undefined, {
      type: `${REORDER_PROVIDERS}_SUCCESS`,
    });

    expect(state.data).toBe(true);
  });

  it('keeps whether the caller may export, from the listing', () => {
    const state = providersExportable(undefined, {
      type: `${LIST_PROVIDERS}_SUCCESS`,
      result: { items: [], can_export: true },
    });

    expect(state.data).toBe(true);
  });

  it('assumes the caller may not export when the listing does not say', () => {
    // A backend from before the flag existed: no buttons rather than
    // buttons that answer 403.
    const state = providersExportable(undefined, {
      type: `${LIST_PROVIDERS}_SUCCESS`,
      result: { items: [] },
    });

    expect(state.data).toBe(false);
  });
});
