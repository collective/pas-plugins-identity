import { describe, expect, it } from 'vitest';

import { interpolate } from './i18n';

describe('interpolate', () => {
  it('fills plain placeholders, and leaves a missing one as written', () => {
    expect(interpolate('Taking you to {provider}…', { provider: 'Dex' })).toBe(
      'Taking you to Dex…',
    );
    expect(interpolate('{a} and {b}', { a: 'one' })).toBe('one and {b}');
  });

  it('chooses the plural branch, with # as the number', () => {
    const fields = '{count, plural, one {# field} other {# fields}}';

    expect(interpolate(fields, { count: 1 })).toBe('1 field');
    expect(interpolate(fields, { count: 4 })).toBe('4 fields');
  });

  it('prefers an exact branch over the category', () => {
    expect(
      interpolate('{n, plural, =0 {none} one {# one} other {# many}}', {
        n: 0,
      }),
    ).toBe('none');
  });

  it("follows the reader's language", () => {
    const text = '{n, plural, one {# one} few {# few} other {# other}}';

    expect(interpolate(text, { n: 3 }, 'en')).toBe('3 other');
    expect(interpolate(text, { n: 3 }, 'pl')).toBe('3 few');
  });

  it('fills a plural inside a sentence, beside plain placeholders', () => {
    expect(
      interpolate(
        'Up to {minutes, plural, one {# minute} other {# minutes}} for {app}.',
        { minutes: 5, app: 'Dex' },
      ),
    ).toBe('Up to 5 minutes for Dex.');
  });

  it('leaves a plural without its value as written', () => {
    const text = '{count, plural, one {# field} other {# fields}}';

    expect(interpolate(text, {})).toBe(text);
  });
});
