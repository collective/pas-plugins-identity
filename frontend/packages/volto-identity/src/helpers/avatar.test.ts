import { beforeEach, describe, expect, it } from 'vitest';
import config from '@plone/volto/registry';

import {
  DEFAULT_AVATAR_COLORS,
  avatarColors,
  colorFor,
  initialsFor,
} from './avatar';

const USERIDS = ['alice', 'bob', '', 'a'.repeat(200), 'ürico'];

/**
 * Configure a palette the way a project does.
 *
 * @param colors The palette.
 */
function configure(colors: string[]) {
  config.settings.identity = { showPloneLogin: false, avatarColors: colors };
}

/**
 * Return a colour's relative luminance, as WCAG 2 defines it.
 *
 * @param hex A `#rrggbb` colour.
 * @returns The luminance, from 0 for black to 1 for white.
 */
function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5]
    .map((start) => parseInt(hex.slice(start, start + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

beforeEach(() => {
  delete (config.settings as Record<string, unknown>).identity;
});

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
    for (const userid of USERIDS) {
      expect(DEFAULT_AVATAR_COLORS).toContain(colorFor(userid) as never);
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
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor(undefined) as never);
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor(null) as never);
  });

  it("picks from a project's own palette", () => {
    const palette = ['#111111', '#222222', '#333333'];
    configure(palette);

    for (const userid of USERIDS) {
      expect(palette).toContain(colorFor(userid));
    }
  });
});

describe('avatarColors', () => {
  it('is the shipped palette when nothing is configured', () => {
    expect(avatarColors()).toEqual(DEFAULT_AVATAR_COLORS);
  });

  it('is the configured palette when a project sets one', () => {
    configure(['#111111']);

    expect(avatarColors()).toEqual(['#111111']);
  });

  it('treats an empty palette as none', () => {
    // A palette with no colour cannot pick one: every avatar would be drawn
    // with no background at all.
    configure([]);

    expect(avatarColors()).toEqual(DEFAULT_AVATAR_COLORS);
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor('alice') as never);
  });

  it.each([...DEFAULT_AVATAR_COLORS])(
    'ships %s, which clears WCAG AA against the white initials',
    (hex) => {
      // 4.5:1, the ratio for normal text: the initials are well under the
      // size WCAG counts as large at the 30px the toolbar draws them.
      const ratio = (luminance('#ffffff') + 0.05) / (luminance(hex) + 0.05);

      expect(ratio).toBeGreaterThanOrEqual(4.5);
    },
  );
});
