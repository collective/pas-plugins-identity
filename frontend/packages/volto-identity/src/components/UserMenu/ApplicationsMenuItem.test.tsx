import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import ApplicationsMenuItem from './ApplicationsMenuItem';

interface State {
  /** The signed-in user, or nobody. */
  userid?: string | null;
  /** The `@oauth-grants` request state. */
  grants?: Record<string, unknown>;
}

/**
 * Render the plug the way Volto's user menu does.
 *
 * @param state What the store says.
 * @returns The dispatch spy, so a test can see whether it asked.
 */
function renderInMenu(state: State = {}) {
  const { userid = 'alice', grants = {} } = state;
  const dispatch = vi.fn();
  const store = {
    getState: () => ({
      userProfile: { data: userid ? { id: userid } : null },
      oauthGrants: grants,
    }),
    dispatch,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as never}>
      <MemoryRouter>
        <PluggablesProvider>
          <ApplicationsMenuItem />
          <ul>
            <Pluggable name="toolbar-user-menu" />
          </ul>
        </PluggablesProvider>
      </MemoryRouter>
    </Provider>,
  );
  return { dispatch };
}

/** The entry, if it rendered. */
const entry = () => screen.queryByRole('link', { name: 'Applications' });

describe('ApplicationsMenuItem', () => {
  it('links to the applications page once the endpoint answered', () => {
    renderInMenu({ grants: { loaded: true } });

    expect(entry()?.getAttribute('href')).toBe('/applications');
  });

  it('renders nothing on a site without the [server] layer', () => {
    // Nothing publishes `@oauth-grants` there, so the entry would lead to a
    // page that can only report a failure.
    renderInMenu({ grants: { error: new Error('404') } });

    expect(entry()).toBeNull();
  });

  it('renders nothing before the answer arrives', () => {
    renderInMenu({ grants: { loading: true } });

    expect(entry()).toBeNull();
  });

  it('asks the endpoint once somebody is signed in', () => {
    const { dispatch } = renderInMenu();

    expect(dispatch).toHaveBeenCalled();
  });

  it('asks nothing for an anonymous visitor', () => {
    // `appExtras` mounts this on every route, logged in or not, and asking
    // would be a guaranteed 401 on every anonymous page view.
    const { dispatch } = renderInMenu({ userid: null });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not ask again once it has an answer', () => {
    const { dispatch } = renderInMenu({ grants: { loaded: true } });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not retry a site that answered 404', () => {
    // Retrying on every render would be a request loop rather than a
    // feature detection.
    const { dispatch } = renderInMenu({ grants: { error: new Error('404') } });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not ask twice while one request is in flight', () => {
    const { dispatch } = renderInMenu({ grants: { loading: true } });

    expect(dispatch).not.toHaveBeenCalled();
  });
});
