import { describe, expect, it } from 'vitest';

import type { AccountIdentity, AuditEvent } from '../types';
import {
  AUTHENTICATED,
  fillPlaceholders,
  providerTitle,
  recentSignIns,
} from './welcome';

const VALUES = { username: 'alice', fullname: 'Alice Liddell' };

/**
 * One audit event.
 *
 * @param event The event name.
 * @param provider The provider it came from.
 * @param timestamp When it happened.
 * @param success Whether it succeeded.
 * @returns The event.
 */
function event(
  event: string,
  provider: string,
  timestamp: string,
  success = true,
): AuditEvent {
  return { event, provider, success, timestamp, detail: {} };
}

describe('fillPlaceholders', () => {
  it('fills in both placeholders', () => {
    expect(fillPlaceholders('Hello {fullname} ({username})!', VALUES)).toBe(
      'Hello Alice Liddell (alice)!',
    );
  });

  it('fills in a placeholder every time it appears', () => {
    expect(fillPlaceholders('{username}, {username}', VALUES)).toBe(
      'alice, alice',
    );
  });

  it('leaves a name that is not a placeholder as it was', () => {
    // So a typo shows on the page rather than vanishing from it.
    expect(fillPlaceholders('Hello {fulname}!', VALUES)).toBe(
      'Hello {fulname}!',
    );
  });

  it('does not reach through to what every object inherits', () => {
    expect(fillPlaceholders('{constructor} {toString}', VALUES)).toBe(
      '{constructor} {toString}',
    );
  });

  it('inserts a value as it is, braces and all', () => {
    // A name is not a template, and filling one in is not a second pass.
    expect(
      fillPlaceholders('Hello {fullname}!', {
        username: 'alice',
        fullname: '{username}',
      }),
    ).toBe('Hello {username}!');
  });
});

describe('recentSignIns', () => {
  it('takes the newest sign-in and the one before it', () => {
    const events = [
      event(AUTHENTICATED, 'github', '2026-09-12T10:00:00'),
      event('identity-linked', 'google', '2026-09-11T10:00:00'),
      event(AUTHENTICATED, 'email', '2026-09-10T10:00:00'),
      event(AUTHENTICATED, 'github', '2026-09-01T10:00:00'),
    ];

    const { current, previous } = recentSignIns(events);

    expect(current?.provider).toBe('github');
    expect(current?.timestamp).toBe('2026-09-12T10:00:00');
    expect(previous?.provider).toBe('email');
  });

  it('skips a sign-in that failed', () => {
    const { current } = recentSignIns([
      event(AUTHENTICATED, 'github', '2026-09-12T10:00:00', false),
      event(AUTHENTICATED, 'email', '2026-09-10T10:00:00'),
    ]);

    expect(current?.provider).toBe('email');
  });

  it('answers null for what the log does not hold', () => {
    expect(recentSignIns([])).toEqual({ current: null, previous: null });
    expect(
      recentSignIns([event(AUTHENTICATED, 'github', '2026-09-12T10:00:00')])
        .previous,
    ).toBeNull();
  });
});

describe('providerTitle', () => {
  const IDENTITIES = [
    { provider: 'github', title: 'GitHub' },
    { provider: 'email', title: '' },
  ] as AccountIdentity[];

  it('names the provider by the title its identity carries', () => {
    expect(providerTitle('github', IDENTITIES)).toBe('GitHub');
  });

  it('falls back to the id', () => {
    // An identity since unlinked, or one whose provider has no title.
    expect(providerTitle('google', IDENTITIES)).toBe('google');
    expect(providerTitle('email', IDENTITIES)).toBe('email');
  });
});
