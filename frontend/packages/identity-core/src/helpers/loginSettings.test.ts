import { describe, expect, it } from 'vitest';

import { asBoolean, asksToChoose, CHOOSE_LOGIN_PATH } from './loginSettings';

describe('asksToChoose', () => {
  it('is false for a plain login page', () => {
    expect(asksToChoose('')).toBe(false);
    expect(asksToChoose('?came_from=%2Fnews')).toBe(false);
  });

  it('is true when the parameter is there, beside others or alone', () => {
    expect(asksToChoose('?choose=1')).toBe(true);
    expect(asksToChoose('?came_from=%2Fnews&choose=1')).toBe(true);
    expect(asksToChoose('?choose')).toBe(true);
  });

  it('does not match a parameter that only starts the same', () => {
    expect(asksToChoose('?chooser=1')).toBe(false);
  });

  it('is what the path the callback links to asks for', () => {
    const { pathname, search } = new URL(CHOOSE_LOGIN_PATH, 'http://site');

    expect(pathname).toBe('/login');
    expect(asksToChoose(search)).toBe(true);
  });
});

describe('asBoolean', () => {
  it('falls back when the variable is not set', () => {
    expect(asBoolean(undefined, false)).toBe(false);
    expect(asBoolean(undefined, true)).toBe(true);
  });

  it('treats an empty value as unset', () => {
    // `docker compose` writes an empty string for a variable named with no
    // value, which means "I said nothing", not "I said no".
    expect(asBoolean('', true)).toBe(true);
  });

  it.each(['1', 'true', 'TRUE', 'yes', 'on', ' true '])(
    'reads %o as on',
    (value) => {
      expect(asBoolean(value, false)).toBe(true);
    },
  );

  it.each(['0', 'false', 'FALSE', 'no', 'off'])('reads %o as off', (value) => {
    // The one that matters: `Boolean("false")` is `true`, which would turn an
    // operator switching the password form off into a site that still has it.
    expect(asBoolean(value, true)).toBe(false);
  });

  it('reads anything it does not recognise as off', () => {
    // Rather than as on: the values this gates are ones a site opts into.
    expect(asBoolean('maybe', true)).toBe(false);
  });
});
