import { describe, expect, it } from 'vitest';

import { EXPORT_PROVIDERS, REORDER_PROVIDERS } from '../constants/ActionTypes';
import { exportProviders, reorderProviders } from './providers';

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

  it('exports every provider when none is named', () => {
    const action = exportProviders();

    expect(action.type).toBe(EXPORT_PROVIDERS);
    expect(action.request).toEqual({
      op: 'get',
      path: '/@identity-providers/@export',
    });
  });

  it('exports the one provider named', () => {
    expect(exportProviders('github').request).toEqual({
      op: 'get',
      path: '/@identity-providers/github/export',
    });
  });
});
