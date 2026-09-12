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
const { showPloneLogin, SHOW_PLONE_LOGIN_ENV } = await import(
  './showPloneLogin'
);

/**
 * Configure the default the way a project does.
 *
 * @param showPloneLogin The configured default.
 */
function configure(showPloneLogin: boolean) {
  config.settings.identity = { showPloneLogin, avatarColors: [] };
}

describe('showPloneLogin', () => {
  beforeEach(() => {
    delete runtime[SHOW_PLONE_LOGIN_ENV];
    delete (config.settings as Record<string, unknown>).identityShowPloneLogin;
    configure(false);
  });

  it('is off when nothing says otherwise', () => {
    expect(showPloneLogin()).toBe(false);
  });

  it('is on when the environment says so', () => {
    // The whole point of the change: this value arrives at run time, so one
    // image serves a site that wants the password form and one that does not.
    runtime[SHOW_PLONE_LOGIN_ENV] = 'true';

    expect(showPloneLogin()).toBe(true);
  });

  it('reads the word "false" as off', () => {
    // Not `Boolean(value)`, which reads the string "false" as true and turns
    // an operator switching the form *off* into a site that still shows it.
    configure(true);
    runtime[SHOW_PLONE_LOGIN_ENV] = 'false';

    expect(showPloneLogin()).toBe(false);
  });

  it('falls back to the setting when the environment is silent', () => {
    // So a project shipping its own default keeps it.
    configure(true);

    expect(showPloneLogin()).toBe(true);
  });

  it('treats an empty variable as silence rather than as off', () => {
    // An unset variable and one set to nothing reach the container the same
    // way, and neither is an operator asking for the form to go away.
    configure(true);
    runtime[SHOW_PLONE_LOGIN_ENV] = '';

    expect(showPloneLogin()).toBe(true);
  });

  it('lets the environment override the setting in both directions', () => {
    configure(true);
    runtime[SHOW_PLONE_LOGIN_ENV] = 'off';
    expect(showPloneLogin()).toBe(false);

    configure(false);
    runtime[SHOW_PLONE_LOGIN_ENV] = 'on';
    expect(showPloneLogin()).toBe(true);
  });

  it('no longer reads the old top-level setting', () => {
    // `config.settings.identityShowPloneLogin` moved under `identity`. A
    // project still setting the old key gets the default, not its old answer.
    (config.settings as Record<string, unknown>).identityShowPloneLogin = true;

    expect(showPloneLogin()).toBe(false);
  });

  it('is off when the add-on settings are missing entirely', () => {
    // Before `install` has run, or in a test that never ran it.
    delete (config.settings as Record<string, unknown>).identity;

    expect(showPloneLogin()).toBe(false);
    runtime[SHOW_PLONE_LOGIN_ENV] = 'true';
    expect(showPloneLogin()).toBe(true);
  });

  it('survives a runtimeConfig that carries nothing', () => {
    // Volto builds it by filtering `process.env` for `RAZZLE_*`, so a
    // container with none is an empty object rather than an error.
    expect(() => showPloneLogin()).not.toThrow();
  });
});
