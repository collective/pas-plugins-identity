import { describe, expect, it } from 'vitest';
import i18next from 'i18next';

import { CATALOGUE, translateWith } from './i18n';

async function germanT() {
  const i18n = i18next.createInstance();
  await i18n.init({
    lng: 'de',
    fallbackLng: false,
    ns: ['common'],
    defaultNS: 'common',
    resources: {
      de: {
        common: {
          [CATALOGUE]: {
            Password: 'Passwort',
            'That login name and password did not match.':
              'Anmeldename und Passwort passen nicht zusammen.',
            'Taking you to {provider}…': 'Sie werden zu {provider} geleitet…',
          },
          // Aurora's own keys, nested the usual way, to show they are not
          // disturbed.
          cmsui: { auth: { signIn: 'Anmelden' } },
        },
      },
    },
  });
  return i18n.getFixedT('de', 'common');
}

describe('translateWith', () => {
  it("reads a translation from the add-on's catalogue", async () => {
    const t = translateWith(await germanT());

    expect(t({ id: 'Password', defaultMessage: 'Password' })).toBe('Passwort');
  });

  it('reads an id full of the separators i18next would split on', async () => {
    const t = translateWith(await germanT());

    expect(
      t({
        id: 'That login name and password did not match.',
        defaultMessage: 'That login name and password did not match.',
      }),
    ).toBe('Anmeldename und Passwort passen nicht zusammen.');
  });

  it('fills placeholders the way the catalogues write them', async () => {
    const t = translateWith(await germanT());

    expect(
      t(
        {
          id: 'Taking you to {provider}…',
          defaultMessage: 'Taking you to {provider}…',
        },
        { provider: 'GitHub' },
      ),
    ).toBe('Sie werden zu GitHub geleitet…');
  });

  it('falls back to the English text it was given', async () => {
    const t = translateWith(await germanT());

    expect(
      t(
        { id: 'Sign in with {name}', defaultMessage: 'Sign in with {name}' },
        {
          name: 'Dex',
        },
      ),
    ).toBe('Sign in with Dex');
  });

  it("leaves Aurora's own keys alone", async () => {
    const t = await germanT();
    translateWith(t);

    expect(t('cmsui.auth.signIn')).toBe('Anmelden');
  });
});
