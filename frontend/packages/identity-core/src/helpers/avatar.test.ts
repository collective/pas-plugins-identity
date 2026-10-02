import { describe, expect, it } from 'vitest';

import {
  DEFAULT_AVATAR_COLORS,
  colorFor,
  initialsFor,
  paletteOrDefault,
} from './avatar';

describe('paletteOrDefault', () => {
  it('is the shipped palette when nothing is configured', () => {
    expect(paletteOrDefault(undefined)).toEqual(DEFAULT_AVATAR_COLORS);
    expect(paletteOrDefault(null)).toEqual(DEFAULT_AVATAR_COLORS);
  });

  it('is the configured palette when one is given', () => {
    expect(paletteOrDefault(['#111111'])).toEqual(['#111111']);
  });

  it('treats an empty palette as none', () => {
    expect(paletteOrDefault([])).toEqual(DEFAULT_AVATAR_COLORS);
  });
});

describe('colorFor', () => {
  it('picks from the shipped palette by default', () => {
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor('alice'));
  });

  it('is stable for a userid', () => {
    expect(colorFor('alice')).toBe(colorFor('alice'));
  });

  it('picks from the palette it is given', () => {
    expect(colorFor('alice', ['#111111'])).toBe('#111111');
  });

  it('copes with no userid', () => {
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor(undefined));
    expect(DEFAULT_AVATAR_COLORS).toContain(colorFor(null));
  });
});

describe('initialsFor', () => {
  it('takes the first letters of the first and last words', () => {
    expect(initialsFor('Érico de Andrei')).toBe('ÉA');
  });

  it('takes two letters of a single word', () => {
    expect(initialsFor('alice')).toBe('AL');
  });

  it('is empty when the name has no letter', () => {
    expect(initialsFor('  42 ')).toBe('');
    expect(initialsFor(undefined)).toBe('');
  });
});
