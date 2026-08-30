import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import { Provider } from 'react-redux';
import { MemoryRouter, useLocation } from 'react-router-dom';
import React from 'react';

import { LOGIN } from '@plone/volto/constants/ActionTypes';
import Callback from './Callback';

/**
 * Render the callback route with a store whose state we control.
 *
 * The component is the whole of the frontend's half of a login, and it had no
 * test at all -- which is how it shipped fetching a token successfully and
 * then doing nothing with it, leaving the page on "Signing you in…" with a
 * 200 in the access log.
 */
function fakeStore(state: any) {
  // react-redux only needs the store contract, and `redux` is not a
  // dependency of this package.
  const dispatched: any[] = [];
  return {
    dispatched,
    store: {
      getState: () => state,
      dispatch: (action: any) => {
        dispatched.push(action);
        return action;
      },
      subscribe: () => () => {},
    },
  };
}

/**
 * Reports where the router currently is.
 *
 * These used to assert on `window.location.href`, because the component set
 * it. It routes now, so the observable thing is the router's location -- and
 * asserting on that is also what proves the page is no longer being thrown
 * away to navigate.
 */
function Where() {
  return <span data-testid="where">{useLocation().pathname}</span>;
}

function renderCallback(state: any, search = '?code=abc&state=xyz') {
  const { store, dispatched } = fakeStore(state);
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={[`/login-identity${search}`]}>
        <Callback />
        <Where />
      </MemoryRouter>
    </Provider>,
  );
  return { dispatched };
}

const PENDING = { identityCallback: { loading: true }, magicLinkConfirm: {} };

describe('Callback', () => {
  beforeEach(() => {
    // jsdom refuses a real navigation; the component only ever sets href.
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  it('says it is working while the exchange is in flight', () => {
    renderCallback(PENDING);

    expect(screen.getByRole('status').textContent).toContain('Signing you in');
  });

  it('signs the user in once the token arrives', () => {
    // Volto's persistAuthToken subscribes to the store and writes any new
    // userSession.token out to the cookie, so dispatching its LOGIN_SUCCESS
    // *is* the sign-in. Without this the page never left "Signing you in…".
    const { dispatched } = renderCallback({
      identityCallback: { loaded: true, data: { token: 'a-token' } },
      magicLinkConfirm: {},
    });

    expect(
      dispatched.some(
        (action) =>
          action.type === `${LOGIN}_SUCCESS` &&
          action.result?.token === 'a-token',
      ),
    ).toBe(true);
  });

  it('sends the user where the flow started', () => {
    renderCallback({
      identityCallback: {
        loaded: true,
        data: { token: 'a-token', came_from: '/some/page' },
      },
      magicLinkConfirm: {},
    });

    expect(screen.getByTestId('where').textContent).toBe('/some/page');
  });

  it('falls back to the site root when the flow named nowhere', () => {
    renderCallback({
      identityCallback: { loaded: true, data: { token: 'a-token' } },
      magicLinkConfirm: {},
    });

    expect(screen.getByTestId('where').textContent).toBe('/');
  });

  it('lets a caller override what happens with the token', () => {
    const onToken = vi.fn();
    const { store } = fakeStore({
      identityCallback: {
        loaded: true,
        data: { token: 'a-token', came_from: '/x' },
      },
      magicLinkConfirm: {},
    });
    render(
      <Provider store={store as any}>
        <MemoryRouter initialEntries={['/login-identity?code=a&state=b']}>
          <Callback onToken={onToken} />
        </MemoryRouter>
      </Provider>,
    );

    expect(onToken).toHaveBeenCalledWith('a-token', '/x');
    // The override replaces the default rather than running alongside it.
    // The override replaced the default, so nothing navigated.
    expect(window.location.href).toBe('');
  });

  it('renders inside the login card, not against the window edge', () => {
    // It is the login page one redirect later. Rendered as a bare div it had
    // no container at all, so its one line sat glued to the left edge.
    renderCallback(PENDING);

    expect(document.querySelector('#page-login .loginForm')).toBeTruthy();
    expect(
      document.querySelector('.loginForm .identity-callback'),
    ).toBeTruthy();
  });

  it('leaves the description strip out, having nothing to put in it', () => {
    renderCallback(PENDING);

    expect(document.querySelector('#page-login .description')).toBeNull();
  });

  it('reports a refusal rather than waiting forever', () => {
    renderCallback({
      identityCallback: { error: { status: 401 } },
      magicLinkConfirm: {},
    });

    expect(screen.getByRole('alert').textContent).toContain('no longer valid');
  });

  it('reports a callback that carries no credential at all', () => {
    renderCallback(PENDING, '?nothing=here');

    expect(screen.getByRole('alert').textContent).toContain('incomplete');
  });

  it('reports a provider that refused', () => {
    renderCallback(PENDING, '?error=access_denied');

    expect(screen.getByRole('alert').textContent).toContain('refused');
  });
});

describe('Callback and a confirmation link', () => {
  beforeEach(() => {
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  it('sends the user back to their identities', () => {
    // A confirmation link arrives on the same route, carrying the same
    // `magic_link` parameter as a login link. Only the answer says which one
    // it was -- and without this branch the page sat on "Signing you in…"
    // waiting for a token that is never issued.
    renderCallback(
      {
        identityCallback: {},
        magicLinkConfirm: {
          loaded: true,
          data: { linked: { provider: 'email', subject: 'erico@plone.org' } },
        },
      },
      '?magic_link=a-token',
    );

    expect(screen.getByTestId('where').textContent).toBe('/identities');
  });

  it('does not sign anybody in', () => {
    // The caller already had a session, and answering a confirmation with a
    // fresh one would turn a stolen link into a login.
    const { dispatched } = renderCallback(
      {
        identityCallback: {},
        magicLinkConfirm: {
          loaded: true,
          data: { linked: { provider: 'email', subject: 'erico@plone.org' } },
        },
      },
      '?magic_link=a-token',
    );

    expect(dispatched.some((a: any) => a.type === `${LOGIN}_SUCCESS`)).toBe(
      false,
    );
  });

  it('says what it is doing while confirming', () => {
    renderCallback(
      {
        identityCallback: {},
        magicLinkConfirm: {
          loaded: true,
          data: { linked: { provider: 'email', subject: 'erico@plone.org' } },
        },
      },
      '?magic_link=a-token',
    );

    expect(screen.getByRole('status').textContent).toContain(
      'Confirming your address',
    );
  });
});
