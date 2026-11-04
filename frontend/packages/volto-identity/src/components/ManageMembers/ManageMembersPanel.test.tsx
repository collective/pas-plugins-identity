import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '../../testing';
import React from 'react';

import ManageMembersPanel from './ManageMembersPanel';
import type { ManageMembersPanelProps } from './ManageMembersPanel';
import { groupMember, groupMembersPage } from '../../stories/fixtures';

const DEVELOPERS = groupMember('developers', 'Developers', {
  type: 'group',
  through: ['staff'],
});
const BOB = groupMember('bob', 'Bob Cratchit');

/**
 * Render the panel.
 *
 * @param props What this test is about.
 * @returns The removal callback.
 */
function renderPanel(props: Partial<ManageMembersPanelProps> = {}) {
  const onRemove = vi.fn();
  render(
    <ManageMembersPanel
      title="Staff"
      groupId="staff"
      groupUrl="/identity-profiles/staff"
      result={groupMembersPage([DEVELOPERS, BOB], { can_manage: true })}
      refused={false}
      query=""
      candidateQuery=""
      onCandidateQuery={() => {}}
      candidates={[]}
      searching={false}
      busy={false}
      onAdd={() => {}}
      removing={null}
      onRemove={onRemove}
      {...props}
    />,
  );
  return onRemove;
}

/**
 * The row for one member.
 *
 * @param id The member's id.
 * @returns The row.
 */
const row = (id: string) =>
  document.querySelector(`[data-member="${id}"]`) as HTMLElement;

describe('ManageMembersPanel', () => {
  it('names the group and links back to it', () => {
    renderPanel();

    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(
      'Members of Staff',
    );
    expect(
      screen
        .getByRole('link', { name: 'Back to the group' })
        .getAttribute('href'),
    ).toBe('/identity-profiles/staff');
  });

  it('lists nested groups and people, and says which is a group', () => {
    renderPanel();

    expect(within(row('developers')).getByText('Group')).toBeTruthy();
    expect(within(row('bob')).queryByText('Group')).toBeNull();
  });

  it('removes the member whose button is pressed', () => {
    const onRemove = renderPanel();

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Remove Bob Cratchit from this group',
      }),
    );

    expect(onRemove).toHaveBeenCalledWith(BOB);
  });

  it('removes with a trash icon, named for the member it removes', () => {
    renderPanel();

    const button = screen.getByRole('button', {
      name: 'Remove Bob Cratchit from this group',
    });
    expect(button.textContent).toBe('');
    expect(button.querySelector('svg')).toBeTruthy();
  });

  it('holds every row while one is being removed', () => {
    renderPanel({ removing: 'bob' });

    const buttons = screen.getAllByRole('button', { name: /^Remove / });
    expect(buttons.every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
  });

  it('offers the add form', () => {
    renderPanel();

    expect(screen.getByLabelText('Find people or groups')).toBeTruthy();
  });

  it('never offers the group as a member of itself', () => {
    renderPanel({
      candidateQuery: 'sta',
      candidates: [
        { id: 'staff', title: 'Staff', type: 'group' },
        { id: 'stan', title: 'Stan Laurel', type: 'user' },
      ],
    });

    expect(screen.queryByLabelText(/^Staff/)).toBeNull();
    expect(screen.getByLabelText(/^Stan Laurel/)).toBeTruthy();
  });

  it('pages when there are more members than one page holds', () => {
    renderPanel({
      result: groupMembersPage([DEVELOPERS, BOB], {
        can_manage: true,
        items_total: 37,
      }),
    });

    expect(
      screen.getByRole('navigation', { name: 'Pages of members' }),
    ).toBeTruthy();
  });

  it('says so while the members are loading', () => {
    renderPanel({ result: null });

    expect(screen.getByRole('status').textContent).toBe('Loading members…');
  });

  it('says so when nobody is in the group itself', () => {
    renderPanel({ result: groupMembersPage([], { can_manage: true }) });

    expect(
      screen.getByText('Nobody is in this group itself yet.'),
    ).toBeTruthy();
  });

  it('says so when a search matches nobody', () => {
    renderPanel({
      query: 'zelda',
      result: groupMembersPage([], { can_manage: true }),
    });

    expect(
      screen.getByText('Nobody in this group matches “zelda”.'),
    ).toBeTruthy();
  });

  it('offers nothing to somebody who may not change the members', () => {
    renderPanel({ refused: true });

    expect(
      screen.getByText(/You cannot change who is in this group/),
    ).toBeTruthy();
    expect(screen.queryByLabelText('Find people or groups')).toBeNull();
    expect(screen.queryByRole('button', { name: /^Remove / })).toBeNull();
  });
});
