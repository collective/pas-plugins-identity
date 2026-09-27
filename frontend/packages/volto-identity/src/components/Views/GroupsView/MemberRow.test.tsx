import { describe, expect, it } from 'vitest';
import { render, screen } from '../../../testing';
import React from 'react';

import MemberRow from './MemberRow';
import type { GroupMember } from '../../../types';

const ALICE: GroupMember = {
  '@id': '/identity-profiles/alice',
  id: 'alice',
  fullname: 'Alice Liddell',
  login: 'alice@example.com',
  profile_url: '/identity-profiles/alice',
  through: ['developers'],
};

/**
 * Render one row, in the list it always sits in.
 *
 * @param member The person.
 */
function renderRow(member: GroupMember): void {
  render(
    <ul>
      <MemberRow member={member} groupId="staff" />
    </ul>,
  );
}

describe('MemberRow', () => {
  it('links a member who has a profile', () => {
    renderRow(ALICE);

    const link = screen.getByText('Alice Liddell') as HTMLAnchorElement;
    expect(link.tagName).toBe('A');
    expect(link.getAttribute('href')).toBe('/identity-profiles/alice');
  });

  it('does not link one who has none', () => {
    // An account that predates the add-on, or a site not keeping users as
    // content: there is nowhere to send the reader.
    renderRow({ ...ALICE, profile_url: null });

    expect((screen.getByText('Alice Liddell') as HTMLElement).tagName).toBe(
      'SPAN',
    );
  });

  it('says which group an inherited member came through', () => {
    renderRow({ ...ALICE, through: ['developers', 'contractors'] });

    expect(screen.getByText('through developers, contractors')).toBeTruthy();
  });

  it('says nothing extra about a direct member', () => {
    renderRow({ ...ALICE, through: ['staff'] });

    expect(screen.queryByText(/through/)).toBeNull();
  });

  it('says nothing extra about somebody who is in it both ways', () => {
    // Directly, and through a nested group as well: they are a direct member.
    renderRow({ ...ALICE, through: ['developers', 'staff'] });

    expect(screen.queryByText(/through/)).toBeNull();
  });
});
