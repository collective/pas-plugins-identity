import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * Stand in for Volto's `runtimeConfig`.
 *
 * A stable object whose keys the tests mutate, because the helper reads it at
 * call time rather than binding a value at import.
 */
const { runtime } = vi.hoisted(() => ({
  runtime: {} as Record<string, string | undefined>,
}));

vi.mock('@plone/volto/runtime_config', () => ({ runtimeConfig: runtime }));

const { default: config } = await import('@plone/volto/registry');
const { redirectToSoleProvider, REDIRECT_TO_SOLE_PROVIDER_ENV } = await import(
  './redirectToSoleProvider'
);

/**
 * Configure the default the way a project does.
 *
 * @param redirectToSoleProvider The configured default.
 */
function configure(redirectToSoleProvider: boolean) {
  config.settings.identity = {
    showPloneLogin: false,
    redirectToSoleProvider,
    avatarColors: [],
  };
}

describe('redirectToSoleProvider', () => {
  beforeEach(() => {
    delete runtime[REDIRECT_TO_SOLE_PROVIDER_ENV];
    configure(true);
  });

  it('is on when nothing says otherwise', () => {
    // What the login page did before this was a setting.
    expect(redirectToSoleProvider()).toBe(true);
  });

  it('is off when the setting says so', () => {
    configure(false);

    expect(redirectToSoleProvider()).toBe(false);
  });

  it('is off when the environment says so', () => {
    runtime[REDIRECT_TO_SOLE_PROVIDER_ENV] = 'false';

    expect(redirectToSoleProvider()).toBe(false);
  });

  it('lets the environment override the setting in both directions', () => {
    configure(true);
    runtime[REDIRECT_TO_SOLE_PROVIDER_ENV] = 'off';
    expect(redirectToSoleProvider()).toBe(false);

    configure(false);
    runtime[REDIRECT_TO_SOLE_PROVIDER_ENV] = 'on';
    expect(redirectToSoleProvider()).toBe(true);
  });

  it('treats an empty variable as silence rather than as off', () => {
    configure(false);
    runtime[REDIRECT_TO_SOLE_PROVIDER_ENV] = '';
    expect(redirectToSoleProvider()).toBe(false);

    configure(true);
    expect(redirectToSoleProvider()).toBe(true);
  });

  it('is on when the add-on settings are missing entirely', () => {
    // Before `install` has run. The default is on, so a missing setting
    // cannot read as `false` the way `Boolean(undefined)` would.
    delete (config.settings as Record<string, unknown>).identity;

    expect(redirectToSoleProvider()).toBe(true);
    runtime[REDIRECT_TO_SOLE_PROVIDER_ENV] = 'false';
    expect(redirectToSoleProvider()).toBe(false);
  });
});
