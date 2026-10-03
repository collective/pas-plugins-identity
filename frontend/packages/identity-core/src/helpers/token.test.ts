import { describe, expect, it } from 'vitest';

import { expiryFromToken, useridFromToken } from './token';

/**
 * Build a JWT-shaped string around a payload.
 *
 * Only the middle segment is ever read, so the other two are noise on
 * purpose: anything that started depending on them would be a bug.
 */
function tokenFor(payload: unknown): string {
  const body = Buffer.from(JSON.stringify(payload))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `header.${body}.signature`;
}

describe('useridFromToken', () => {
  it('reads the subject', () => {
    expect(useridFromToken(tokenFor({ sub: 'alice', exp: 1 }))).toBe('alice');
  });

  it('handles a payload whose base64 needs padding', () => {
    // A JWT drops the `=` padding, so a payload whose length is not a
    // multiple of four is the normal case rather than an edge one.
    const userid = 'a'.repeat(7);

    expect(useridFromToken(tokenFor({ sub: userid }))).toBe(userid);
  });

  it('handles base64url characters', () => {
    // `-` and `_` stand in for `+` and `/`; decoding without translating
    // them back yields mojibake rather than an error, which is the kind of
    // bug that only shows up for some users.
    const userid = 'ürico?andrei>plone';

    expect(useridFromToken(tokenFor({ sub: userid }))).toBe(userid);
  });

  it('answers nobody when there is no token', () => {
    expect(useridFromToken(undefined)).toBe('');
    expect(useridFromToken(null)).toBe('');
    expect(useridFromToken('')).toBe('');
  });

  it('answers nobody for something that is not a JWT', () => {
    // This runs inside a component rendered on every page, so a malformed
    // token has to be an empty answer rather than an exception.
    expect(useridFromToken('not-a-jwt')).toBe('');
    expect(useridFromToken('a.b.c')).toBe('');
  });

  it('answers nobody when the payload carries no subject', () => {
    expect(useridFromToken(tokenFor({ exp: 1 }))).toBe('');
  });

  it('answers nobody when the subject is not a string', () => {
    expect(useridFromToken(tokenFor({ sub: 42 }))).toBe('');
  });
});

describe('expiryFromToken', () => {
  it('reads the exp claim as a date', () => {
    expect(
      expiryFromToken(tokenFor({ sub: 'alice', exp: 1700000000 })),
    ).toEqual(new Date(1700000000 * 1000));
  });

  it('is null for a token without one', () => {
    expect(expiryFromToken(tokenFor({ sub: 'alice' }))).toBeNull();
  });

  it('is null for an exp that is not a number', () => {
    expect(expiryFromToken(tokenFor({ exp: 'soon' }))).toBeNull();
  });

  it('is null when there is no usable token', () => {
    expect(expiryFromToken(undefined)).toBeNull();
    expect(expiryFromToken('not-a-jwt')).toBeNull();
    expect(expiryFromToken('a.!!!.c')).toBeNull();
  });
});
