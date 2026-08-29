/**
 * The shadowed users-control-panel row.
 *
 * What is pinned here is the one thing that differs from Volto: where Edit
 * leads. A user whose fields live in a Profile is edited on that Profile; a
 * user whose fields live in `portal_memberdata` still gets Volto's modal.
 * Both halves matter — the second is the site's own `admin`, and any account
 * that predates the add-on and has not signed in since.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';
import { Table } from 'semantic-ui-react';

import RenderUsers, { profileEditUrl } from './RenderUsers';

const ROLES = [{ id: 'Member' }, { id: 'Manager' }];

const USERSCHEMA = {
  loaded: true,
  userschema: { properties: {}, fieldsets: [] },
};

function renderRow(user: Record<string, unknown>) {
  // One state object, not a fresh literal per call: the component selects
  // `users.update` out of it, and `useSelector` compares by identity — a new
  // object every `getState` is an infinite re-render.
  const state = { users: { update: { loading: false } } };
  const store = {
    getState: () => state,
    dispatch: vi.fn(),
    subscribe: () => () => {},
  };
  return render(
    <Provider store={store as never}>
      <MemoryRouter>
        <Table>
          <Table.Body>
            <RenderUsers
              user={
                {
                  '@id': 'http://localhost:8080/Plone/@users/alice',
                  id: 'alice',
                  username: 'alice',
                  fullname: 'Alice Liddell',
                  roles: [],
                  source: 'source_users',
                  identities: [],
                  profile_url: null,
                  ...user,
                } as never
              }
              roles={ROLES}
              isUserManager={true}
              updateUser={vi.fn()}
              onDelete={vi.fn()}
              userschema={USERSCHEMA}
            />
          </Table.Body>
        </Table>
      </MemoryRouter>
    </Provider>,
  );
}

describe('profileEditUrl', () => {
  it('is the Profile edit form, app-relative', () => {
    expect(profileEditUrl('http://localhost:8080/Plone/profiles/alice')).toBe(
      '/profiles/alice/edit',
    );
  });

  it('is nothing for a user with no Profile', () => {
    // Which is what leaves Volto's member-properties modal in place for
    // them: the site's own admin, and anyone else with no Profile.
    expect(profileEditUrl(null)).toBeNull();
    expect(profileEditUrl(undefined)).toBeNull();
    expect(profileEditUrl('')).toBeNull();
  });
});

describe('RenderUsers', () => {
  it('links Edit to the Profile when the user has one', () => {
    // The defect this fixes: the modal edits `portal_memberdata`, which is
    // not where this user's fields are read from, and shows only the fields
    // `@userschema` happens to name.
    renderRow({ profile_url: 'http://localhost:8080/Plone/profiles/alice' });

    const edit = document.querySelector('#edit-user-button');

    expect(edit?.tagName).toBe('A');
    expect(edit?.getAttribute('href')).toBe('/profiles/alice/edit');
  });

  it('leaves the modal in place for a user without a Profile', () => {
    renderRow({ profile_url: null });

    const edit = document.querySelector('#edit-user-button');

    expect(edit).not.toBeNull();
    expect(edit?.tagName).not.toBe('A');
  });

  it('still offers Delete either way', () => {
    // The row keeps working: the change is the destination of one entry, not
    // the menu it is in.
    renderRow({ profile_url: 'http://localhost:8080/Plone/profiles/alice' });

    expect(document.querySelector('#delete-user-button')).not.toBeNull();
  });

  it('shows the user the way the panel always has', () => {
    renderRow({});

    expect(screen.getByText(/Alice Liddell/)).toBeTruthy();
  });
});
