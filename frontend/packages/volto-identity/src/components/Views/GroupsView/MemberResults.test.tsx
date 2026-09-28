import { describe, expect, it } from 'vitest';
import { render, screen } from '../../../testing';
import React from 'react';

import MemberResults from './MemberResults';
import type { GroupMember, GroupMembers } from '../../../types';

const ALICE: GroupMember = {
  '@id': '/identity-profiles/alice',
  id: 'alice',
  fullname: 'Alice Liddell',
  login: 'alice@example.com',
  profile_url: '/identity-profiles/alice',
  through: ['developers'],
};

const BOB: GroupMember = {
  '@id': '/identity-profiles/bob',
  id: 'bob',
  fullname: 'Bob Cratchit',
  login: 'bob@example.com',
  profile_url: null,
  through: ['staff'],
};

/**
 * A search answered with `items`.
 *
 * @param items The rows on the first page.
 * @param total How many matched in all.
 * @returns The listing.
 */
function found(items: GroupMember[], total = items.length): GroupMembers {
  return {
    '@id': '/@group-members/staff',
    group: 'staff',
    items,
    items_total: total,
    members_total: 42,
    direct_members_total: 12,
    nested_groups: [],
    parent_groups: [],
  };
}

describe('MemberResults', () => {
  it('asks for a search before anybody has searched', () => {
    render(<MemberResults groupId="staff" query="" result={null} />);

    expect(screen.getByText(/Search by name or login/)).toBeTruthy();
  });

  it('lists nobody before anybody has searched, whatever it is given', () => {
    // The summary request carries a first page of rows; not drawing them is
    // the point.
    render(<MemberResults groupId="staff" query="" result={found([ALICE])} />);

    expect(screen.queryByText('Alice Liddell')).toBeNull();
  });

  it('says so while the search is on its way', () => {
    render(<MemberResults groupId="staff" query="ali" result={null} />);

    expect(screen.getByRole('status').textContent).toBe('Searching…');
  });

  it('lists what the search found', () => {
    render(
      <MemberResults groupId="staff" query="li" result={found([ALICE, BOB])} />,
    );

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
    expect(screen.getByText('Bob Cratchit')).toBeTruthy();
  });

  it('says so when nobody matches', () => {
    render(<MemberResults groupId="staff" query="zelda" result={found([])} />);

    expect(
      screen.getByText('Nobody in this group matches “zelda”.'),
    ).toBeTruthy();
  });

  it('says when there are more matches than one page shows', () => {
    render(
      <MemberResults
        groupId="staff"
        query="example"
        result={found([ALICE, BOB], 31)}
      />,
    );

    expect(screen.getByText(/Showing 2 of 31 matches/)).toBeTruthy();
  });

  it('says nothing more when one page holds every match', () => {
    render(
      <MemberResults groupId="staff" query="li" result={found([ALICE, BOB])} />,
    );

    expect(screen.queryByText(/Showing/)).toBeNull();
  });
});
