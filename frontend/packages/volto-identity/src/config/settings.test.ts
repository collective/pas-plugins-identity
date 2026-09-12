import { describe, expect, it } from 'vitest';

import install from './settings';

import { asBoolean } from './settings';
import { DEFAULT_AVATAR_COLORS } from '../helpers/avatar';

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

describe('install', () => {
  function configured() {
    const config: any = { settings: {} };
    install(config);
    return config;
  }

  it('asks for the profile alongside every content request', () => {
    // The gate needs the answer on every navigation, and a navigation to a
    // content route is already a request. Without this entry it stays two.
    const entry = configured().settings.apiExpanders.find((e: any) =>
      e.GET_CONTENT?.includes('my-profile'),
    );

    expect(entry).toBeDefined();
    expect(entry.match).toBe('');
  });

  it('keeps the expanders Volto or another add-on already registered', () => {
    // Assigning rather than appending would drop `breadcrumbs`, `navroot` and
    // the rest, which is a broken site rather than a missing feature.
    const config: any = {
      settings: { apiExpanders: [{ match: '', GET_CONTENT: ['navroot'] }] },
    };
    install(config);

    const asked = config.settings.apiExpanders.flatMap(
      (e: any) => e.GET_CONTENT ?? [],
    );
    expect(asked).toContain('navroot');
    expect(asked).toContain('my-profile');
  });

  it('offers every setting under config.settings.identity', () => {
    expect(configured().settings.identity).toEqual({
      showPloneLogin: false,
      avatarColors: [...DEFAULT_AVATAR_COLORS],
    });
  });

  it('puts nothing of its own directly on config.settings', () => {
    // `identityShowPloneLogin` lived there. A project reading it would get a
    // stale answer, so it is not set at all.
    expect(configured().settings).not.toHaveProperty('identityShowPloneLogin');
  });

  it('hands out a copy of the shipped palette', () => {
    // A project pushing a colour onto its palette must not change the
    // default that `avatarColors()` falls back to.
    const { avatarColors } = configured().settings.identity;
    avatarColors.push('#000000');

    expect(avatarColors).not.toBe(DEFAULT_AVATAR_COLORS);
    expect(DEFAULT_AVATAR_COLORS).toHaveLength(10);
  });

  it('keeps what an add-on configured before it', () => {
    // These are defaults: an add-on listed ahead of this one may already
    // have chosen a palette to match its theme.
    const config: any = {
      settings: { identity: { avatarColors: ['#111111'] } },
    };
    install(config);

    expect(config.settings.identity).toEqual({
      showPloneLogin: false,
      avatarColors: ['#111111'],
    });
  });
});
