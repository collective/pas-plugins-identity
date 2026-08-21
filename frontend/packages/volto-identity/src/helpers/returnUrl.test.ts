import { describe, expect, it } from 'vitest';

import { returnUrl } from './returnUrl';

describe('returnUrl', () => {
  it('uses an explicit return_url', () => {
    expect(returnUrl('?return_url=/some/page', '/login')).toBe('/some/page');
  });

  it('accepts came_from too', () => {
    expect(returnUrl('?came_from=/some/page', '/login')).toBe('/some/page');
  });

  it('falls back to the site root from /login', () => {
    expect(returnUrl('', '/login')).toBe('/');
  });

  it('strips a trailing /login from a nested path', () => {
    expect(returnUrl('', '/a/folder/login')).toBe('/a/folder');
  });

  it.each([
    'https://evil.example/phish',
    '//evil.example/phish',
    'http://evil.example',
  ])('refuses the off-site target %s', (target) => {
    // S6, on the frontend too: the backend drops these as well, but a target
    // that never leaves the browser would never reach the backend to be
    // checked.
    expect(
      returnUrl(`?return_url=${encodeURIComponent(target)}`, '/login'),
    ).toBe('/');
  });

  it('refuses a relative target that is not rooted', () => {
    expect(returnUrl('?return_url=some/page', '/login')).toBe('/');
  });

  it('ignores a repeated parameter rather than guessing', () => {
    expect(returnUrl('?return_url=/a&return_url=/b', '/login')).toBe('/');
  });
});
