import { describe, expect, it } from 'vitest';

import { AVATAR_COLORS, colorFor, initialsFor } from './avatar';

describe('initialsFor', () => {
  it('takes the first letter of the first and last words', () => {
    expect(initialsFor('Érico Andrei')).toBe('ÉA');
  });

  it('skips the middle names rather than the surname', () => {
    // ÉA, not ÉD: a middle name must not push the surname out.
    expect(initialsFor('Érico de Andrei')).toBe('ÉA');
  });

  it('takes two letters from a single name', () => {
    expect(initialsFor('madonna')).toBe('MA');
  });

  it('takes one letter from a single-letter name', () => {
    expect(initialsFor('x')).toBe('X');
  });

  it('uppercases for the locale', () => {
    expect(initialsFor('érico andrei')).toBe('ÉA');
  });

  it('ignores words that carry no letter', () => {
    // A userid like `alice (admin)` should not yield `A(`.
    expect(initialsFor('alice (admin)')).toBe('AA');
    // `bob - 2` has exactly one lettered word, so it is the single-name
    // case: two letters from `bob`, not `B` twice.
    expect(initialsFor('bob - 2')).toBe('BO');
  });

  it('answers nothing when there is no name at all', () => {
    // The component draws a plain circle rather than an empty box.
    expect(initialsFor('')).toBe('');
    expect(initialsFor('   ')).toBe('');
    expect(initialsFor(undefined)).toBe('');
    expect(initialsFor(null)).toBe('');
  });

  it('answers nothing for a name with no letters in it', () => {
    expect(initialsFor('123 456')).toBe('');
  });

  it('handles a name outside the Latin alphabet', () => {
    expect(initialsFor('Ада Лавлейс')).toBe('АЛ');
  });
});

describe('colorFor', () => {
  it('always picks from the palette', () => {
    for (const userid of ['alice', 'bob', '', 'a'.repeat(200), 'ürico']) {
      expect(AVATAR_COLORS).toContain(colorFor(userid) as never);
    }
  });

  it('is stable for the same user', () => {
    // The point of deriving it: the same person is the same colour on every
    // visit and every device, with nothing stored anywhere.
    expect(colorFor('alice')).toBe(colorFor('alice'));
  });

  it('separates users who sit next to each other', () => {
    // Not a guarantee for every pair -- ten colours cannot be -- but
    // adjacent userids landing on one colour would be visible immediately.
    const colors = new Set(
      ['alice', 'bob', 'carol', 'dave'].map((id) => colorFor(id)),
    );

    expect(colors.size).toBeGreaterThan(1);
  });

  it('answers for a user with no id', () => {
    expect(AVATAR_COLORS).toContain(colorFor(undefined) as never);
    expect(AVATAR_COLORS).toContain(colorFor(null) as never);
  });
});
