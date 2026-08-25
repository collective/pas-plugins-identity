import { describe, expect, it } from 'vitest';

import { asBoolean } from './settings';

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
