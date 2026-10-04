import { describe, expect, it } from 'vitest';

import {
  DEFAULT_SETTINGS,
  loginSettings,
  REDIRECT_TO_SOLE_PROVIDER_ENV,
  SHOW_PLONE_LOGIN_ENV,
} from './settings';

describe('loginSettings', () => {
  it("defaults to the Volto add-on's answers", () => {
    expect(loginSettings(undefined, {})).toEqual({
      showPloneLogin: false,
      redirectToSoleProvider: true,
    });
    expect(loginSettings(undefined, {})).toEqual(DEFAULT_SETTINGS);
  });

  it('takes the configured settings over the defaults', () => {
    expect(
      loginSettings(
        { showPloneLogin: true, redirectToSoleProvider: false },
        {},
      ),
    ).toEqual({ showPloneLogin: true, redirectToSoleProvider: false });
  });

  it('takes the environment over the configured settings', () => {
    expect(
      loginSettings(
        { showPloneLogin: false, redirectToSoleProvider: true },
        {
          [SHOW_PLONE_LOGIN_ENV]: 'true',
          [REDIRECT_TO_SOLE_PROVIDER_ENV]: 'false',
        },
      ),
    ).toEqual({ showPloneLogin: true, redirectToSoleProvider: false });
  });

  it('reads an empty variable as unset', () => {
    expect(
      loginSettings({ showPloneLogin: true }, { [SHOW_PLONE_LOGIN_ENV]: '' }),
    ).toMatchObject({ showPloneLogin: true });
  });
});
