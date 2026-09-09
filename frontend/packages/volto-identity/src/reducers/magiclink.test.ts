import { describe, expect, it } from 'vitest';

import { SEND_MAGIC_LINK } from '../constants/ActionTypes';
import { magicLinkSend } from './magiclink';

describe('magicLinkSend', () => {
  it('records that a link went out', () => {
    const state = magicLinkSend(undefined, {
      type: `${SEND_MAGIC_LINK}_SUCCESS`,
      result: { sent: true },
    });

    expect(state.data).toBe(true);
  });

  it('does not treat a rate-limited refusal as sent', () => {
    const state = magicLinkSend(undefined, {
      type: `${SEND_MAGIC_LINK}_FAIL`,
      error: { status: 429 },
    });

    expect(state.data).toBe(false);
    expect(state.error).toEqual({ status: 429 });
  });
});
