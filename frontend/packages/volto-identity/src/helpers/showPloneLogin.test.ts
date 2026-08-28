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

describe('showPloneLogin', () => {
  beforeEach(() => {
    delete runtime[SHOW_PLONE_LOGIN_ENV];
    config.settings.identityShowPloneLogin = false;
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
    config.settings.identityShowPloneLogin = true;
    runtime[SHOW_PLONE_LOGIN_ENV] = 'false';

    expect(showPloneLogin()).toBe(false);
  });

  it('falls back to the setting when the environment is silent', () => {
    // So a project shipping its own default keeps it.
    config.settings.identityShowPloneLogin = true;

    expect(showPloneLogin()).toBe(true);
  });

  it('treats an empty variable as silence rather than as off', () => {
    // An unset variable and one set to nothing reach the container the same
    // way, and neither is an operator asking for the form to go away.
    config.settings.identityShowPloneLogin = true;
    runtime[SHOW_PLONE_LOGIN_ENV] = '';

    expect(showPloneLogin()).toBe(true);
  });

  it('lets the environment override the setting in both directions', () => {
    config.settings.identityShowPloneLogin = true;
    runtime[SHOW_PLONE_LOGIN_ENV] = 'off';
    expect(showPloneLogin()).toBe(false);

    config.settings.identityShowPloneLogin = false;
    runtime[SHOW_PLONE_LOGIN_ENV] = 'on';
    expect(showPloneLogin()).toBe(true);
  });

  it('survives a runtimeConfig that carries nothing', () => {
    // Volto builds it by filtering `process.env` for `RAZZLE_*`, so a
    // container with none is an empty object rather than an error.
    expect(() => showPloneLogin()).not.toThrow();
  });
});
