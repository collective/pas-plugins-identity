import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import Login from './Login';
import * as showPloneLoginModule from '../../helpers/showPloneLogin';

/**
 * Replace `window.location` so a navigation can be observed instead of
 * performed; jsdom refuses to navigate and would fail the test instead.
 */
function captureNavigation() {
  const original = window.location;
  const navigated: string[] = [];
  // jsdom's location is not writable through the normal assignment.
  delete (window as any).location;
  // @ts-expect-error a stub with only what the component touches
  window.location = {
    ...original,
    get href() {
      return original.href;
    },
    set href(value: string) {
      navigated.push(value);
    },
  };
  return {
    navigated,
    restore: () =>
      Object.defineProperty(window, 'location', {
        value: original,
        writable: true,
      }),
  };
}

/**
 * The listing slice as the reducer leaves it after a successful request.
 *
 * `loaded` is not decoration here: it is the flag the page uses to tell "the
 * providers are not here yet" from "there are none", so a fixture without it
 * is a fixture of a request that never answered.
 */
const LOADED_PROVIDERS = {
  loading: false,
  loaded: true,
  error: null,
  data: [{ id: 'github', title: 'GitHub' }],
};

function storeWith(token?: string, loginProviders: any = LOADED_PROVIDERS) {
  const state = {
    loginProviders,
    providerLogin: {},
    magicLinkSend: {},
    userSession: { token, login: {} },
  };
  return {
    getState: () => state,
    dispatch: (action: any) => action,
    subscribe: () => () => {},
  };
}

function renderLogin(
  token?: string,
  search = '?came_from=%2F%40%40oauth-authorize',
  loginProviders?: any,
) {
  render(
    <Provider store={storeWith(token, loginProviders) as any}>
      <MemoryRouter initialEntries={[`/login${search}`]}>
        <Login />
      </MemoryRouter>
    </Provider>,
  );
}

describe('Login', () => {
  let capture: ReturnType<typeof captureNavigation>;

  beforeEach(() => {
    capture = captureNavigation();
  });

  afterEach(() => {
    capture.restore();
    vi.restoreAllMocks();
  });

  it('does not redirect when the visitor already had a session', () => {
    // This page is only reached because something refused that session --
    // an authorization endpoint that will not accept the principal. Bouncing
    // back to it is an infinite redirect, and the sign-in buttons never stay
    // on screen long enough to be clicked.
    renderLogin('an-existing-token');

    expect(capture.navigated).toEqual([]);
  });

  it('shows the providers instead of redirecting', () => {
    renderLogin('an-existing-token');

    expect(document.body.textContent).toContain('GitHub');
  });

  it('asks at render time whether to offer the password form', () => {
    // Not read from the settings at install: the answer arrives in the
    // container's environment, so one image serves a site that wants the
    // password form and one that does not. Severing this wiring is invisible
    // to every other test here, which is why it has one of its own.
    const decide = vi
      .spyOn(showPloneLoginModule, 'showPloneLogin')
      .mockReturnValue(true);

    renderLogin('an-existing-token');

    expect(decide).toHaveBeenCalled();
    expect(document.body.textContent).toContain('Sign in with a password');
  });

  it('hides the password form when the environment says to', () => {
    vi.spyOn(showPloneLoginModule, 'showPloneLogin').mockReturnValue(false);

    renderLogin('an-existing-token');

    expect(document.body.textContent).not.toContain('Sign in with a password');
  });

  it('does not redirect an anonymous visitor either', () => {
    renderLogin(undefined);

    expect(capture.navigated).toEqual([]);
  });

  it('waits rather than guessing before the listing has answered', () => {
    // The slice as it is on the very first render: the effect has not
    // dispatched yet, so it is neither loading nor loaded. Reading only
    // `loading` and `data` made that indistinguishable from a site with no
    // providers, and the page rendered the local password form -- the
    // no-providers fallback -- for a tick before replacing it.
    renderLogin(undefined, undefined, {
      loading: false,
      loaded: false,
      error: null,
      data: [],
    });

    expect(document.body.textContent).toContain('Loading');
    expect(document.body.textContent).not.toContain('Sign in with a password');
    expect(document.querySelector('#login-form-submit')).toBeNull();
  });

  it('names what is below only once it knows', () => {
    // The description strip is the same guess in prose. Naming the local
    // password form and then replacing the sentence is the flicker with
    // words instead of fields.
    renderLogin(undefined, undefined, {
      loading: true,
      loaded: false,
      error: null,
      data: [],
    });

    expect(document.body.textContent).not.toContain(
      'Sign in with your account on this site.',
    );
    expect(document.body.textContent).not.toContain(
      'Choose how you would like to sign in.',
    );
  });

  it('falls back to the password form when the listing fails', () => {
    // A failure has answered -- with nothing. Holding the loading state for
    // it would leave a site whose provider list is unreachable with a
    // spinner instead of the one way in that still works.
    renderLogin(undefined, undefined, {
      loading: false,
      loaded: false,
      error: { status: 500 },
      data: [],
    });

    expect(document.body.textContent).not.toContain('Loading');
    expect(document.querySelector('#login-form-submit')).toBeTruthy();
  });
});
