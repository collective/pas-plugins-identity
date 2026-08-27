/**
 * The gate, mounted.
 *
 * `helpers/profileGate` already covers which path wins; what is left is the
 * wiring around it, and every one of these is a way to break a site rather
 * than a component. Asking for the profile while anonymous answers 401 on
 * every page of a public site. Not asking at all leaves a user with an
 * unfinished profile browsing freely. Redirecting before the answer arrives,
 * or after an error, makes a backend hiccup look like a locked site.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, useLocation } from 'react-router-dom';
import { Provider } from 'react-redux';

import ProfileGate from './ProfileGate';

const PROFILE = 'https://example.org/identity-profiles/alice';

const dispatched: any[] = [];

function store(state: any) {
  return {
    getState: () => state,
    subscribe: () => () => {},
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
  };
}

function profileState(overrides: any = {}) {
  return {
    loading: false,
    loaded: true,
    error: null,
    data: {
      '@id': '/@my-profile',
      userid: 'alice',
      profile: PROFILE,
      review_state: 'incomplete',
    },
    ...overrides,
  };
}

/** Render the gate at a path and report where the router ended up. */
function mountAt(pathname: string, state: any): { path: string } {
  const seen = { path: pathname };
  const Spy = () => {
    seen.path = useLocation().pathname;
    return null;
  };
  render(
    <Provider store={store(state) as any}>
      <MemoryRouter initialEntries={[pathname]}>
        <ProfileGate />
        <Route path="*" component={Spy} />
      </MemoryRouter>
    </Provider>,
  );
  return seen;
}

describe('ProfileGate', () => {
  it('sends a user with an unfinished profile to its edit form', () => {
    const seen = mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: profileState(),
    });

    expect(seen.path).toBe('/identity-profiles/alice/edit');
  });

  it('leaves a finished profile where it was going', () => {
    const seen = mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: profileState({
        data: {
          '@id': '/@my-profile',
          userid: 'alice',
          profile: PROFILE,
          review_state: 'complete',
        },
      }),
    });

    expect(seen.path).toBe('/news');
  });

  it('does not redirect before the answer has arrived', () => {
    const seen = mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: { loading: true, loaded: false, error: null },
    });

    expect(seen.path).toBe('/news');
  });

  it('does not redirect when the backend answered with an error', () => {
    // A backend that cannot answer must not be able to make the site
    // unreachable. The worst case of letting somebody through is that they
    // fill their profile in later.
    const seen = mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: { loading: false, loaded: false, error: { status: 500 } },
    });

    expect(seen.path).toBe('/news');
  });

  it('asks for the profile once when there is a session', () => {
    dispatched.length = 0;

    mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: { loading: false, loaded: false, error: null },
    });

    expect(dispatched.length).toBe(1);
  });

  it('asks for nothing while anonymous', () => {
    // Every page of a public site would otherwise answer 401 to a request
    // nobody made.
    dispatched.length = 0;

    mountAt('/news', {
      userSession: {},
      myProfile: { loading: false, loaded: false, error: null },
    });

    expect(dispatched.length).toBe(0);
  });

  it('renders nothing', () => {
    const { container } = render(
      <Provider
        store={
          store({
            userSession: { token: 'a-token' },
            myProfile: profileState(),
          }) as any
        }
      >
        <MemoryRouter initialEntries={['/identity-profiles/alice/edit']}>
          <ProfileGate />
        </MemoryRouter>
      </Provider>,
    );

    expect(container.innerHTML).toBe('');
  });
});
