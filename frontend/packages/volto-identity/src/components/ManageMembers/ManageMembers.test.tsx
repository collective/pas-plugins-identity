/**
 * The page as a whole: what it loads, and what it sends.
 *
 * What each part draws is tested with `ManageMembersPanel` and `AddMembers`.
 * What is left here is which endpoint each change goes to -- every one of
 * them an endpoint that already exists.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '../../testing';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

import ManageMembers, { toCandidates } from './ManageMembers';
import {
  LIST_DIRECT_GROUP_MEMBERS,
  UNNEST_GROUP,
} from '../../constants/ActionTypes';
import {
  groupContent,
  groupMember,
  groupMembersPage,
} from '../../stories/fixtures';

// Chrome around the panel rather than anything this test is about, and it
// reads store slices this page does not own. `vi.mock` is hoisted above the
// imports, so it takes effect despite sitting below them.
vi.mock('@plone/volto/components/manage/Toolbar/Toolbar', () => ({
  default: () => null,
}));

const LOADED = { loading: false, loaded: true, error: null };

const DEVELOPERS = groupMember('developers', 'Developers', {
  type: 'group',
  through: ['everyone', 'staff'],
});
const BOB = groupMember('bob', 'Bob Cratchit');

/**
 * Render the page against an inert store.
 *
 * @param listing The `groupDirectMembers` slot.
 * @param url Where the page is open.
 * @returns Every action the page dispatched.
 */
function renderPage(
  listing: any = {
    ...LOADED,
    data: groupMembersPage([DEVELOPERS, BOB], { can_manage: true }),
  },
  url = '/identity-profiles/staff/manage-members',
): any[] {
  const dispatched: any[] = [];
  // Built once: a selector handed a new object on every read never settles.
  const state = {
    content: { data: groupContent() },
    groupDirectMembers: listing,
    users: { users: [], list: LOADED },
    groups: { groups: [], list: LOADED },
  };
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
      <MemoryRouter initialEntries={[url]}>
        <ManageMembers />
      </MemoryRouter>
    </Provider>,
  );
  return dispatched;
}

describe('ManageMembers', () => {
  beforeEach(() => {
    const toolbar = document.createElement('div');
    toolbar.id = 'toolbar';
    document.body.appendChild(toolbar);
  });

  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  it('loads a page of the direct members', () => {
    const dispatched = renderPage();

    const list = dispatched.find((a) => a.type === LIST_DIRECT_GROUP_MEMBERS);
    expect(list.request.path).toBe('/@group-members/staff?direct=1&b_size=10');
  });

  it('loads the page and the search in the URL', () => {
    const dispatched = renderPage(
      undefined,
      '/identity-profiles/staff/manage-members?q=bo&page=2',
    );

    const list = dispatched.find((a) => a.type === LIST_DIRECT_GROUP_MEMBERS);
    expect(list.request.path).toBe(
      '/@group-members/staff?query=bo&direct=1&b_size=10&b_start=10',
    );
  });

  it('removes a person through plone.restapi', async () => {
    const dispatched = renderPage();

    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', {
          name: 'Remove Bob Cratchit from this group',
        }),
      );
    });

    const update = dispatched.find((a) => a.type === 'UPDATE_GROUP');
    expect(update.request).toEqual({
      op: 'patch',
      path: '/@groups/staff',
      data: { users: { bob: false } },
    });
  });

  it('removes a nested group by writing its own memberships', async () => {
    // plone.restapi cannot: it only removes what PlonePAS lists as members,
    // and that list holds userids.
    const dispatched = renderPage();

    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', {
          name: 'Remove Developers from this group',
        }),
      );
    });

    const unnest = dispatched.find((a) => a.type === UNNEST_GROUP);
    expect(unnest.request).toEqual({
      op: 'patch',
      path: '/identity-profiles/developers',
      data: { group_ids: ['everyone'] },
    });
    expect(dispatched.some((a) => a.type === 'UPDATE_GROUP')).toBe(false);
  });

  it('reads the page again after a change', async () => {
    const dispatched = renderPage();
    const before = dispatched.filter(
      (a) => a.type === LIST_DIRECT_GROUP_MEMBERS,
    ).length;

    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', {
          name: 'Remove Bob Cratchit from this group',
        }),
      );
    });

    expect(
      dispatched.filter((a) => a.type === LIST_DIRECT_GROUP_MEMBERS).length,
    ).toBe(before + 1);
  });

  it('refuses a caller the listing says may not change it', () => {
    renderPage({ ...LOADED, data: groupMembersPage([BOB]) });

    expect(
      screen.getByText(/You cannot change who is in this group/),
    ).toBeTruthy();
  });

  it('refuses a caller the listing refused', () => {
    renderPage({ loading: false, loaded: false, error: { status: 403 } });

    expect(
      screen.getByText(/You cannot change who is in this group/),
    ).toBeTruthy();
  });
});

describe('toCandidates', () => {
  it('turns Volto search results into groups, then people', () => {
    const candidates = toCandidates(
      [{ id: 'alice', fullname: 'Alice Liddell', username: 'alice' }],
      [{ id: 'developers', title: 'Developers' }],
    );

    expect(candidates).toEqual([
      { id: 'developers', title: 'Developers', type: 'group' },
      {
        id: 'alice',
        title: 'Alice Liddell',
        type: 'user',
        detail: 'alice',
      },
    ]);
  });

  it('falls back to the id for a person with no name', () => {
    expect(toCandidates([{ id: 'x1' }], [])[0].title).toBe('x1');
  });

  it('copes with nothing searched yet', () => {
    expect(toCandidates(undefined as any, undefined as any)).toEqual([]);
  });
});
