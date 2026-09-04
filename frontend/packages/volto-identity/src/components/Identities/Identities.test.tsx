import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import Identities from './Identities';

// Volto's toolbar reads slices of the store this page does not own and does
// not fill -- content, actions, the breadcrumb trail. It is chrome around the
// panel rather than anything this test is about, so it is stubbed instead of
// fed: the alternative is a fixture of Volto's whole app state, which would
// break on Volto's schedule rather than on this package's. `vi.mock` is
// hoisted above the imports, so it takes effect despite sitting below them.
vi.mock('@plone/volto/components/manage/Toolbar/Toolbar', () => ({
  default: () => null,
}));

/**
 * The container's wiring, which no other test here can see.
 *
 * Both things pinned below are requests and selectors rather than markup:
 * `IdentitiesList` and `ProfileEmails` are rendered with props in their own
 * tests, and a prop handed to them correctly proves nothing about where the
 * container got it. Severing either of these leaves every one of those tests
 * green and the page quietly wrong -- an unexpanded listing makes
 * `canSignInWithLink` false on every site, which reads as "this operator
 * turned the magic link off" rather than as a broken request.
 */

const EMAIL_PROVIDER = {
  '@id': '/@login-providers/email',
  id: 'email',
  title: 'Email',
  driver: 'email',
};

function storeWith(loginProviders: unknown[]) {
  const state = {
    identities: { loading: false, loaded: true, error: null, data: [] },
    linkableProviders: { loading: false, loaded: true, error: null, data: [] },
    loginProviders: {
      loading: false,
      loaded: true,
      error: null,
      data: loginProviders,
    },
    identityLinking: {},
    identityUnlink: {},
    preferredEmail: {},
    myProfile: {
      loading: false,
      loaded: true,
      error: null,
      data: {
        profile: '/identity-profiles/erico',
        emails: [
          { address: 'erico@plone.org', verified: false, preferred: true },
        ],
      },
    },
  };
  return { state, dispatched: [] as any[] };
}

function renderIdentities(loginProviders: unknown[] = [EMAIL_PROVIDER]) {
  const { state, dispatched } = storeWith(loginProviders);
  const store = {
    getState: () => state,
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={['/identities']}>
        <Identities />
      </MemoryRouter>
    </Provider>,
  );
  return { dispatched };
}

/** The addresses live behind their own tab, so a test reaches them by name. */
function openAddresses() {
  fireEvent.click(screen.getByRole('tab', { name: 'Email addresses' }));
}

describe('Identities', () => {
  // The page portals its toolbar into Volto's `#toolbar`, which only the app
  // shell renders. Without it React throws before anything can be asserted.
  beforeEach(() => {
    const toolbar = document.createElement('div');
    toolbar.id = 'toolbar';
    document.body.appendChild(toolbar);
  });

  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  it('asks for the listing with the login providers expanded', () => {
    // Unexpanded, `state.loginProviders` is never filled on this route and
    // the page cannot tell a provider that is off the login page from one
    // that is on it.
    const { dispatched } = renderIdentities();

    const paths = dispatched
      .filter((action) => action?.request?.path)
      .map((action) => action.request.path);
    expect(paths).toContain('/@identities?expand=login-providers');
  });

  it('says a verified address signs you in when email is a way in', () => {
    renderIdentities([EMAIL_PROVIDER]);
    openAddresses();

    expect(document.body.textContent).toContain('sign in with a link');
  });

  it('does not, when the operator took email off the login page', () => {
    // `show_in_login` off: the provider is still enabled and still verifies
    // addresses, but nothing on the login page starts that flow.
    renderIdentities([
      { '@id': '/@login-providers/dex', id: 'dex', driver: 'oidc-generic' },
    ]);
    openAddresses();

    expect(document.body.textContent).not.toContain('sign in with a link');
    expect(document.body.textContent).toContain('recognises you');
  });
});
