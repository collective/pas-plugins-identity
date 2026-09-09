import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import config from '@plone/volto/registry';

import GroupView from './GroupView';
import { groupContent } from '../../stories/fixtures';

const CONTENT = groupContent({
  description: 'Everybody who works here.',
});

const MEMBERS = {
  '@id': '/@group-members/staff',
  group: 'staff',
  items_total: 2,
  items: [
    {
      '@id': '/@group-members/staff/alice',
      id: 'alice',
      fullname: 'Alice Liddell',
      login: 'alice@example.com',
      profile_url: '/identity-profiles/alice',
      through: ['developers'],
    },
    {
      '@id': '/@group-members/staff/bob',
      id: 'bob',
      fullname: 'Bob Cratchit',
      login: 'bob@example.com',
      profile_url: null,
      through: ['staff'],
    },
  ],
  nested_groups: [{ '@id': '/x', id: 'developers', title: 'Developers' }],
  parent_groups: [{ '@id': '/y', id: 'everyone', title: 'Everyone' }],
};

function renderView(state: any = {}) {
  const store = {
    getState: () => ({ groupMembers: state }),
    dispatch: (action: any) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <GroupView content={CONTENT} />
    </Provider>,
  );
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
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.getByText('Staff')).toBeTruthy();
    expect(screen.getByText('Everybody who works here.')).toBeTruthy();
  });

  it('lists the groups nested inside it', () => {
    // The requirement: a group page says what is in it, and membership of an
    // inner group is membership of this one.
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.getByText('Developers')).toBeTruthy();
  });

  it('says what it is nested inside', () => {
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.getByText('Everyone')).toBeTruthy();
  });

  it('lists the members', () => {
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
    expect(screen.getByText('Bob Cratchit')).toBeTruthy();
  });

  it('says which group an inherited member came through', () => {
    // A list that silently mixes direct members with inherited ones is a list
    // nobody can account for.
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.getByText(/through developers/)).toBeTruthy();
  });

  it('says nothing extra about a direct member', () => {
    renderView({ loaded: true, data: MEMBERS });

    expect(screen.queryByText(/through staff/)).toBeNull();
  });

  it('links a member who has a profile', () => {
    renderView({ loaded: true, data: MEMBERS });

    const link = screen.getByText('Alice Liddell') as HTMLAnchorElement;
    expect(link.tagName).toBe('A');
  });

  it('does not link one who has none', () => {
    // An account that predates the add-on, or a site not keeping users as
    // content: there is nowhere to send the reader.
    renderView({ loaded: true, data: MEMBERS });

    expect((screen.getByText('Bob Cratchit') as HTMLElement).tagName).toBe(
      'SPAN',
    );
  });

  it('renders the belowTitle slot between the heading and the description', () => {
    // Under the name, where what belongs to the group reads as part of it.
    // Nothing outside a view can put anything inside one, which is why this
    // slot is rendered here and `aboveContent` is not.
    registerBadge(() => <span>Core team</span>);

    renderView({ loaded: true, data: MEMBERS });

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

  it('says so while the membership is loading', () => {
    renderView({ loading: true });

    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('still renders the group when the membership is refused', () => {
    // A visitor who can see the group without being in it gets the title and
    // description. That is a page, not an error.
    renderView({ error: { status: 403 } });

    expect(screen.getByText('Staff')).toBeTruthy();
    expect(screen.getByText(/visible to its own members/)).toBeTruthy();
  });

  it('says so when nobody is in it', () => {
    renderView({
      loaded: true,
      data: { ...MEMBERS, items: [], nested_groups: [], parent_groups: [] },
    });

    expect(screen.getByText(/Nobody is in this group/)).toBeTruthy();
  });
});
