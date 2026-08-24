import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import Login from './Login';

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

function storeWith(token?: string) {
  const state = {
    loginProviders: {
      loading: false,
      data: [{ id: 'github', title: 'GitHub' }],
    },
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
) {
  render(
    <Provider store={storeWith(token) as any}>
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

  it('does not redirect an anonymous visitor either', () => {
    renderLogin(undefined);

    expect(capture.navigated).toEqual([]);
  });
});
