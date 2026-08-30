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
import { IntlProvider } from '../../testing';

import ProfileGate from './ProfileGate';
import { rememberReturn, takeReturn } from '../../helpers/profileGate';

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
      <IntlProvider locale="en">
        <MemoryRouter initialEntries={[pathname]}>
          <ProfileGate />
          <Route path="*" component={Spy} />
        </MemoryRouter>
      </IntlProvider>
    </Provider>,
  );
  return seen;
}

function withStorage(run: () => void): void {
  const original = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
  const values = new Map<string, string>();
  Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    value: {
      getItem: (k: string) => values.get(k) ?? null,
      setItem: (k: string, v: string) => values.set(k, v),
      removeItem: (k: string) => values.delete(k),
    },
  });
  try {
    run();
  } finally {
    if (original) {
      Object.defineProperty(window, 'sessionStorage', original);
    }
  }
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

  it('asks for the profile when there is a session', () => {
    // And again on every navigation, which is deliberate: saving the form is
    // a navigation, and a stale answer here is a user held on a profile they
    // have already completed.
    dispatched.length = 0;

    mountAt('/news', {
      userSession: { token: 'a-token' },
      myProfile: { loading: false, loaded: false, error: null },
    });

    expect(dispatched.length).toBeGreaterThan(0);
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

  it('says what it wants before sending them away', () => {
    // A user dropped on an edit form with no explanation cannot tell a
    // requirement from a broken site. The backend reports which fields are
    // missing so the message can name them.
    dispatched.length = 0;

    withStorage(() => {
      mountAt('/news', {
        userSession: { token: 'a-token' },
        myProfile: profileState({
          data: {
            '@id': '/@my-profile',
            userid: 'alice',
            profile: PROFILE,
            review_state: 'incomplete',
            missing: ['email', 'fullname'],
          },
        }),
      });
    });

    // Volto's `addMessage` action is flat: {type, id, title, body, level}.
    const message = dispatched.find(
      (action: any) => typeof action?.body === 'string',
    );
    expect(message?.body).toContain('email');
    expect(message?.body).toContain('fullname');
    expect(message?.level).toBe('warning');
  });

  it('returns the user to where they were going once it is complete', () => {
    // The bug Érico hit: held mid-way through signing in to another site,
    // he completed his profile and was left on the identity provider with
    // no way onward.
    withStorage(() => {
      rememberReturn('/@@oauth-authorize?client_id=x');

      const seen = mountAt('/news', {
        userSession: { token: 'a-token' },
        myProfile: profileState({
          data: {
            '@id': '/@my-profile',
            userid: 'alice',
            profile: PROFILE,
            review_state: 'complete',
            missing: [],
          },
        }),
      });

      expect(seen.path).toBe('/@@oauth-authorize');
    });
  });

  it('does not return anybody who was never held', () => {
    withStorage(() => {
      const seen = mountAt('/news', {
        userSession: { token: 'a-token' },
        myProfile: profileState({
          data: {
            '@id': '/@my-profile',
            userid: 'alice',
            profile: PROFILE,
            review_state: 'complete',
            missing: [],
          },
        }),
      });

      expect(seen.path).toBe('/news');
    });
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
        <IntlProvider locale="en">
          <MemoryRouter initialEntries={['/identity-profiles/alice/edit']}>
            <ProfileGate />
          </MemoryRouter>
        </IntlProvider>
      </Provider>,
    );

    expect(container.innerHTML).toBe('');
  });
});

describe('the remembered destination', () => {
  // Volto's test environment provides a `sessionStorage` that accepts writes
  // and returns nothing, so a round trip needs a real one. Installed here
  // rather than globally: the point of the other two tests is what the helper
  // does when storage does *not* work.
  it('comes back once and only once', () => {
    // Twice would send somebody back to a page they had already left.
    withStorage(() => {
      rememberReturn('/news');

      expect(takeReturn()).toBe('/news');
      expect(takeReturn()).toBe(null);
    });
  });

  it('ignores an empty destination', () => {
    withStorage(() => {
      rememberReturn('');

      expect(takeReturn()).toBe(null);
    });
  });

  it('is nothing when none was remembered', () => {
    withStorage(() => {
      expect(takeReturn()).toBe(null);
    });
  });

  it('survives storage refusing to work', () => {
    // Private windows throw outright on sessionStorage in some browsers.
    // Losing the return is a worse journey; throwing is a blank page.
    const original = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      value: {
        getItem: () => {
          throw new Error('nope');
        },
        setItem: () => {
          throw new Error('nope');
        },
        removeItem: () => {
          throw new Error('nope');
        },
      },
    });
    try {
      expect(() => rememberReturn('/news')).not.toThrow();
      expect(takeReturn()).toBe(null);
    } finally {
      if (original) {
        Object.defineProperty(window, 'sessionStorage', original);
      }
    }
  });
});
