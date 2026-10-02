import { describe, expect, it } from 'vitest';

import { readCallback } from './callback';

describe('readCallback', () => {
  it('reads an authorization code', () => {
    const parsed = readCallback('?code=abc&state=xyz&provider=dex');

    expect(parsed.kind).toBe('code');
    expect(parsed.code).toBe('abc');
    expect(parsed.state).toBe('xyz');
    expect(parsed.provider).toBe('dex');
  });

  it('reads a magic link', () => {
    const parsed = readCallback('?magic_link=tok');

    expect(parsed.kind).toBe('magic-link');
    expect(parsed.token).toBe('tok');
  });

  it('reports a provider refusal', () => {
    // Providers signal a refusal by redirecting back with ?error=, not by
    // failing the redirect. Missing this leaves the page spinning forever.
    const parsed = readCallback('?error=access_denied&state=xyz');

    expect(parsed.kind).toBe('error');
    expect(parsed.error).toBe('access_denied');
  });

  it('prefers the refusal over a code that came with it', () => {
    const parsed = readCallback('?error=access_denied&code=abc&state=xyz');

    expect(parsed.kind).toBe('error');
  });

  it('treats a code without a state as incomplete', () => {
    expect(readCallback('?code=abc').kind).toBe('none');
  });

  it('treats a state without a code as incomplete', () => {
    expect(readCallback('?state=xyz').kind).toBe('none');
  });

  it('treats an empty query as incomplete', () => {
    expect(readCallback('').kind).toBe('none');
  });

  it('ignores repeated parameters rather than guessing', () => {
    // qs.parse gives an array for a repeated key. Taking the first would be
    // picking one of two credentials an attacker supplied.
    expect(readCallback('?magic_link=one&magic_link=two').kind).toBe('none');
  });

  it('defaults the provider to empty rather than undefined', () => {
    const parsed = readCallback('?code=abc&state=xyz');

    expect(parsed.provider).toBe('');
  });
});
