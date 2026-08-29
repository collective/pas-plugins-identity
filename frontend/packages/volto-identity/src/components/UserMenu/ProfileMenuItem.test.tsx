import { describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import ProfileMenuItem from './ProfileMenuItem';

/**
 * Render the plug the way Volto's user menu does, over a store holding
 * exactly the profile state the component selects.
 */
function renderInMenu(userProfile: unknown) {
  const store = {
    getState: () => ({ userProfile }),
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as never}>
      <MemoryRouter>
        <PluggablesProvider>
          <ProfileMenuItem />
          <ul>
            <Pluggable name="toolbar-user-menu" />
          </ul>
        </PluggablesProvider>
      </MemoryRouter>
    </Provider>,
  );
}

const loaded = (profileUrl: string | null, source = 'identity_profile') => ({
  loading: false,
  loaded: true,
  error: null,
  data: { id: 'alice', profile_url: profileUrl, source },
});

/** The entry, if it rendered. */
const entry = () => screen.queryByRole('link', { name: 'Profile' });

describe('ProfileMenuItem', () => {
  it('links to the Profile of a user whose account is one', () => {
    renderInMenu(loaded('http://localhost:8080/Plone/identity-profiles/alice'));

    // Flattened: the store holds the backend's absolute URL, and a
    // react-router link has to be a path on this site.
    expect(entry()?.getAttribute('href')).toBe('/identity-profiles/alice');
  });

  it('renders nothing when the user has no Profile', () => {
    // An account that predates the add-on, or a user first login has not
    // minted one for. An entry leading nowhere is worse than no entry.
    renderInMenu(loaded(null));

    expect(entry()).toBeNull();
  });

  it('does not care which plugin authenticated the account', () => {
    // It never could: every account this package creates lives in
    // `source_users`, and keying on that hid this entry for everybody. What
    // decides is whether a Profile holds the user's fields.
    renderInMenu(
      loaded(
        'http://localhost:8080/Plone/identity-profiles/alice',
        'source_users',
      ),
    );

    expect(entry()).toBeTruthy();
  });

  it('renders nothing before the user has loaded', () => {
    renderInMenu({ loading: true, loaded: false, error: null, data: null });

    expect(entry()).toBeNull();
  });

  it('renders nothing for an anonymous visitor', () => {
    // `appExtras` mounts this on every route, logged in or not.
    renderInMenu(undefined);

    expect(entry()).toBeNull();
  });
});
