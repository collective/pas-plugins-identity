/**
 * First-login routing, mounted.
 *
 * `helpers/firstLogin` covers where a given answer sends somebody. What is
 * left is when the question is asked at all: this route is reached with a
 * token in hand, but it is registered like every other route and an anonymous
 * visitor who opens it directly would fire a request that can only answer 401.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, useLocation } from 'react-router-dom';
import { Provider } from 'react-redux';
import config from '@plone/volto/registry';
import { IntlProvider } from '../../testing';

import FirstLogin from './FirstLogin';

/** Render the route and report where the router ended up. */
function landing(state: any): { path: string } {
  const seen = { path: '/first-login' };
  const Spy = () => {
    seen.path = useLocation().pathname;
    return null;
  };
  const store = {
    getState: () => state,
    subscribe: () => () => {},
    dispatch: (action: any) => action,
  };
  render(
    <Provider store={store as any}>
      <IntlProvider locale="en">
        <MemoryRouter initialEntries={['/first-login']}>
          <FirstLogin />
          <Route path="*" component={Spy} />
        </MemoryRouter>
      </IntlProvider>
    </Provider>,
  );
  return seen;
}

function mount(state: any) {
  const dispatched: any[] = [];
  const store = {
    getState: () => state,
    subscribe: () => () => {},
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
  };
  render(
    <Provider store={store as any}>
      <IntlProvider locale="en">
        <MemoryRouter initialEntries={['/first-login']}>
          <FirstLogin />
        </MemoryRouter>
      </IntlProvider>
    </Provider>,
  );
  return dispatched;
}

const PENDING = { loading: false, loaded: false, error: null, data: null };

describe('FirstLogin', () => {
  it('asks for the profile once it has a token', () => {
    expect(
      mount({ userSession: { token: 'a-token' }, myProfile: PENDING }),
    ).toHaveLength(1);
  });

  it('asks for nothing while anonymous', () => {
    expect(mount({ userSession: {}, myProfile: PENDING })).toHaveLength(0);
  });

  it('says what it is doing either way', () => {
    // The panel renders from the component's own state, so an anonymous
    // visitor gets the same page rather than a blank one.
    mount({ userSession: {}, myProfile: PENDING });

    expect(document.querySelector('[role="status"]')).not.toBeNull();
  });

  it("strips the backend's site path when Volto talks to it directly", () => {
    // Without a proxy rewriting URLs, the backend reports the profile under
    // its own site path, which the app's routes do not carry.
    const seen = landing({
      userSession: { token: 'a-token' },
      myProfile: {
        loading: false,
        loaded: true,
        error: null,
        data: {
          '@id': '/@my-profile',
          userid: 'alice',
          profile: `${config.settings.apiPath}/identity-profiles/alice`,
          review_state: 'incomplete',
        },
      },
    });

    expect(config.settings.apiPath).toMatch(/\/[^/]+$/);
    expect(seen.path).toBe('/identity-profiles/alice/edit');
  });
});
