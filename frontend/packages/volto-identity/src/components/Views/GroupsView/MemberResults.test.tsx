import { describe, expect, it } from 'vitest';
import { render, screen } from '../../../testing';
import React from 'react';

import MemberResults from './MemberResults';
import { groupMember, groupMembersPage } from '../../../stories/fixtures';

const ALICE = groupMember('alice', 'Alice Liddell', {
  through: ['developers'],
});

const BOB = groupMember('bob', 'Bob Cratchit', { profile_url: null });

describe('MemberResults', () => {
  it('lists the first page before anybody has searched', () => {
    // The middle ground: a page of people, and a search to narrow them.
    render(
      <MemberResults
        groupId="staff"
        query=""
        result={groupMembersPage([ALICE, BOB])}
      />,
    );

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
    expect(screen.getByText('Bob Cratchit')).toBeTruthy();
  });

  it('says so while the page is on its way', () => {
    render(<MemberResults groupId="staff" query="" result={null} />);

    expect(screen.getByRole('status').textContent).toBe('Loading members…');
  });

  it('says so while a search is on its way', () => {
    render(<MemberResults groupId="staff" query="ali" result={null} />);

    expect(screen.getByRole('status').textContent).toBe('Searching…');
  });

  it('lists what the search found', () => {
    render(
      <MemberResults
        groupId="staff"
        query="li"
        result={groupMembersPage([ALICE, BOB])}
      />,
    );

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
    expect(screen.getByText('Bob Cratchit')).toBeTruthy();
  });

  it('says so when nobody matches', () => {
    render(
      <MemberResults
        groupId="staff"
        query="zelda"
        result={groupMembersPage([])}
      />,
    );

    expect(
      screen.getByText('Nobody in this group matches “zelda”.'),
    ).toBeTruthy();
  });

  it('pages when there are more members than one page holds', () => {
    render(
      <MemberResults
        groupId="staff"
        query=""
        result={groupMembersPage([ALICE, BOB], { items_total: 31 })}
      />,
    );

    expect(
      screen.getByRole('navigation', { name: 'Pages of members' }),
    ).toBeTruthy();
  });

  it('does not page when one page holds every member', () => {
    render(
      <MemberResults
        groupId="staff"
        query=""
        result={groupMembersPage([ALICE, BOB])}
      />,
    );

    expect(screen.queryByRole('navigation')).toBeNull();
  });
});
