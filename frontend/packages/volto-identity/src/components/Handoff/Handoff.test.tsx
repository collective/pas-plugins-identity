import { afterEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import { Provider } from 'react-redux';
import { MemoryRouter, useLocation } from 'react-router-dom';
import React from 'react';

import Handoff, { restartUrl } from './Handoff';
import {
  clearHandoff,
  pendingHandoff,
  storeHandoff,
} from '../../helpers/handoff';
import { tokenFor } from '../../stories/fixtures';

const REQUEST = { returnUrl: 'http://127.0.0.1:8765/callback', state: 'xyz' };

/** Reports where the router is, query string included. */
function Where() {
  const { pathname, search } = useLocation();
  return <span data-testid="where">{`${pathname}${search}`}</span>;
}

/**
 * Render the consent route.
 *
 * @param token The session, if any.
 */
function mount(token?: string) {
  const store = {
    getState: () => ({ userSession: { token, login: {} } }),
    dispatch: (action: any) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={['/login-handoff']}>
        <Handoff />
        <Where />
      </MemoryRouter>
    </Provider>,
  );
}

const where = () => screen.getByTestId('where').textContent;

/** The form Allow submits. */
function allowForm(): HTMLFormElement {
  return screen.getByRole('button', { name: 'Allow' }).closest('form')!;
}

describe('Handoff', () => {
  afterEach(() => {
    clearHandoff();
  });

  it('names the person and the site', () => {
    storeHandoff(REQUEST);
    const claims = btoa(
      JSON.stringify({ sub: 'alice', fullname: 'Alice Liddell' }),
    ).replace(/=+$/, '');

    mount(`header.${claims}.signature`);

    expect(document.body.textContent).toContain(
      `act as Alice Liddell on ${window.location.host}`,
    );
  });

  it('posts the token and the state to the loopback address', () => {
    storeHandoff(REQUEST);
    const token = tokenFor('alice');

    mount(token);

    const form = allowForm();
    expect(form.method).toBe('post');
    expect(form.action).toBe(REQUEST.returnUrl);
    expect(form.enctype).toBe('application/x-www-form-urlencoded');
    expect(
      Object.fromEntries(new FormData(form) as unknown as Iterable<any>),
    ).toEqual({ token, state: 'xyz' });
  });

  it('keeps the form on the page, and stays put, on Allow', () => {
    // collective/volto-authomatic#52: clearing the request on Allow
    // re-rendered the page without the form, mid-submit, and a redirect
    // followed. The browser cancels the POST of a form that is gone.
    storeHandoff(REQUEST);
    mount(tokenFor('alice'));
    const form = allowForm();

    fireEvent.submit(form);

    expect(form.isConnected).toBe(true);
    expect(where()).toBe('/login-handoff');
    // Used once: a second visit has nothing to hand over.
    expect(pendingHandoff()).toBeNull();
  });

  it('sends nothing on Deny, and forgets the request', () => {
    storeHandoff(REQUEST);
    mount(tokenFor('alice'));

    fireEvent.click(screen.getByRole('button', { name: 'Deny' }));

    expect(where()).toBe('/');
    expect(pendingHandoff()).toBeNull();
  });

  it('goes home when nothing is pending', () => {
    mount(tokenFor('alice'));

    expect(where()).toBe('/');
    expect(screen.queryByRole('button', { name: 'Allow' })).toBeNull();
  });

  it('asks somebody signed out to sign in first', () => {
    storeHandoff(REQUEST);

    mount(undefined);

    expect(where()).toBe(restartUrl(REQUEST));
    expect(screen.queryByRole('button', { name: 'Allow' })).toBeNull();
  });
});

describe('restartUrl', () => {
  it('starts the same request again on the login page', () => {
    const url = new URL(restartUrl(REQUEST), 'http://site.invalid');

    expect(url.pathname).toBe('/login');
    expect(url.searchParams.get('return_url')).toBe(REQUEST.returnUrl);
    expect(url.searchParams.get('state')).toBe('xyz');
  });
});
