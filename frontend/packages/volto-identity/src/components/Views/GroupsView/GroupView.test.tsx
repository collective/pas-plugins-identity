/**
 * The page as a whole: what it loads, and which parts it shows when.
 *
 * What each part draws is tested with the part -- `MembersCount`,
 * `GroupLinks`, `MemberSearch`, `MemberResults`, `MemberRow`. What is left
 * here is what only the page decides.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '../../../testing';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

import config from '@plone/volto/registry';

import GroupView from './GroupView';
import {
  LIST_GROUP_MEMBERS,
  SEARCH_GROUP_MEMBERS,
} from '../../../constants/ActionTypes';
import { groupContent } from '../../../stories/fixtures';
import type { GroupMember, GroupMembers } from '../../../types';

const CONTENT = groupContent({
  description: 'Everybody who works here.',
});

const ALICE: GroupMember = {
  '@id': '/identity-profiles/alice',
  id: 'alice',
  fullname: 'Alice Liddell',
  login: 'alice@example.com',
  profile_url: '/identity-profiles/alice',
  through: ['developers'],
};

/** What the page loads on its own: the group's size and its nesting. */
const SUMMARY: GroupMembers = {
  '@id': '/@group-members/staff',
  group: 'staff',
  items_total: 3,
  items: [ALICE],
  members_total: 3,
  direct_members_total: 2,
  nested_groups: [
    {
      '@id': '/@group-members/developers',
      id: 'developers',
      title: 'Developers',
      group_url: '/identity-groups/developers',
    },
  ],
  parent_groups: [
    {
      '@id': '/@group-members/everyone',
      id: 'everyone',
      title: 'Everyone',
      group_url: '/identity-groups/everyone',
    },
  ],
};

const LOADED = { loading: false, loaded: true, error: null };

/**
 * A search answered with `items`.
 *
 * @param items The rows.
 * @returns The search slot's state.
 */
function found(items: GroupMember[]) {
  return {
    ...LOADED,
    data: { ...SUMMARY, items, items_total: items.length },
  };
}

/**
 * Render the view against an inert store, at a URL.
 *
 * @param summary The `groupMembers` slot.
 * @param search The `groupMemberSearch` slot.
 * @param url Where the page is open, `?q=` included.
 * @returns Every action the view dispatched.
 */
function renderView(
  summary: any = {},
  search: any = {},
  url = '/identity-groups/staff',
): any[] {
  const dispatched: any[] = [];
  const store = {
    getState: () => ({ groupMembers: summary, groupMemberSearch: search }),
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={[url]}>
        <GroupView content={CONTENT} />
      </MemoryRouter>
    </Provider>,
  );
  return dispatched;
}

/**
 * Register a component into `belowTitle`, the way a deployment does.
 *
 * @param component What to render.
 */
function registerBadge(component: React.ComponentType<any>): void {
  config.registerSlotComponent({
    slot: 'belowTitle',
    name: 'badge',
    component,
  });
}

// A slot registration is global and outlives the test that made it.
afterEach(() => {
  delete config.slots.belowTitle;
});

describe('GroupView', () => {
  it('shows the title and description', () => {
    renderView({ ...LOADED, data: SUMMARY });

    expect(screen.getByText('Staff')).toBeTruthy();
    expect(screen.getByText('Everybody who works here.')).toBeTruthy();
  });

  it('renders the belowTitle slot between the heading and the description', () => {
    // Under the name, where what belongs to the group reads as part of it.
    // Nothing outside a view can put anything inside one, which is why this
    // slot is rendered here and `aboveContent` is not.
    registerBadge(() => <span>Core team</span>);

    renderView({ ...LOADED, data: SUMMARY });

    const badge = screen.getByText('Core team');
    const heading = screen.getByRole('heading', { level: 1 });
    const description = screen.getByText('Everybody who works here.');
    expect(
      heading.compareDocumentPosition(badge) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      description.compareDocumentPosition(badge) &
        Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  });

  it('says what it is nested inside', () => {
    renderView({ ...LOADED, data: SUMMARY });

    expect(screen.getByRole('heading', { name: 'Part of' })).toBeTruthy();
    expect(screen.getByText('Everyone')).toBeTruthy();
  });

  it('lists the groups nested inside it', () => {
    // The requirement: a group page says what is in it, and membership of an
    // inner group is membership of this one.
    renderView({ ...LOADED, data: SUMMARY });

    expect(
      screen.getByRole('heading', { name: 'Groups in this group' }),
    ).toBeTruthy();
    expect(screen.getByText('Developers')).toBeTruthy();
  });

  it('says how many people are in it', () => {
    renderView({ ...LOADED, data: SUMMARY });

    expect(
      document.querySelector('.identity-members-count')?.textContent,
    ).toContain('3 members');
  });

  it('loads the summary without a query', () => {
    const dispatched = renderView({ ...LOADED, data: SUMMARY });

    const list = dispatched.find((a) => a.type === LIST_GROUP_MEMBERS);
    expect(list.request.path).toBe('/@group-members/staff');
  });

  it('does not list the members until somebody searches', () => {
    // The summary carries a first page of rows; a group everybody is in is
    // exactly the group whose list nobody wants drawn.
    const dispatched = renderView({ ...LOADED, data: SUMMARY });

    expect(screen.queryByText('Alice Liddell')).toBeNull();
    expect(dispatched.some((a) => a.type === SEARCH_GROUP_MEMBERS)).toBe(false);
  });

  it('searches for the query in the URL', () => {
    const dispatched = renderView(
      { ...LOADED, data: SUMMARY },
      found([ALICE]),
      '/identity-groups/staff?q=ali',
    );

    const search = dispatched.find((a) => a.type === SEARCH_GROUP_MEMBERS);
    expect(search.request.path).toBe('/@group-members/staff?query=ali');
  });

  it('shows what the search found beside the counts', () => {
    renderView(
      { ...LOADED, data: SUMMARY },
      found([ALICE]),
      '/identity-groups/staff?q=ali',
    );

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
    expect(document.querySelector('.identity-members-count')).toBeTruthy();
  });

  it('says so while the search is on its way', () => {
    renderView(
      { ...LOADED, data: SUMMARY },
      { loading: true },
      '/identity-groups/staff?q=ali',
    );

    expect(screen.getByRole('status').textContent).toBe('Searching…');
  });

  it('ignores a result that belongs to another group', () => {
    // Left over from the last group page: not an answer about this one.
    renderView(
      { ...LOADED, data: SUMMARY },
      { ...LOADED, data: { ...SUMMARY, group: 'developers', items: [ALICE] } },
      '/identity-groups/staff?q=ali',
    );

    expect(screen.queryByText('Alice Liddell')).toBeNull();
  });

  it('says so while the membership is loading', () => {
    renderView({ loading: true });

    expect(screen.getByRole('status').textContent).toBe('Loading members…');
  });

  it('still renders the group when the membership is refused', () => {
    // A visitor who can see the group without being in it gets the title and
    // description. That is a page, not an error.
    renderView({ error: { status: 403 } });

    expect(screen.getByText('Staff')).toBeTruthy();
    expect(screen.getByText(/visible to its own members/)).toBeTruthy();
  });

  it('offers no search of a membership it may not read', () => {
    renderView({ error: { status: 403 } });

    expect(screen.queryByRole('searchbox')).toBeNull();
  });

  it('says so when nobody is in it, and offers nothing to search', () => {
    renderView({
      ...LOADED,
      data: {
        ...SUMMARY,
        items: [],
        members_total: 0,
        direct_members_total: 0,
      },
    });

    expect(screen.getByText(/Nobody is in this group/)).toBeTruthy();
    expect(screen.queryByRole('searchbox')).toBeNull();
  });
});
