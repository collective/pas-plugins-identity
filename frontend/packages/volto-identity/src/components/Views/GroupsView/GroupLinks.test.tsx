import { describe, expect, it } from 'vitest';
import { render, screen } from '../../../testing';
import React from 'react';

import GroupLinks from './GroupLinks';
import type { NestedGroup } from '../../../types';

const DEVELOPERS: NestedGroup = {
  '@id': '/@group-members/developers',
  id: 'developers',
  title: 'Developers',
  group_url: '/identity-groups/developers',
};

const CONTRACTORS: NestedGroup = {
  '@id': '/@group-members/contractors',
  id: 'contractors',
  title: 'Contractors',
  group_url: null,
};

describe('GroupLinks', () => {
  it('shows its heading and help', () => {
    render(
      <GroupLinks
        title="Groups in this group"
        help="Everybody in these is in this one."
        groups={[DEVELOPERS]}
      />,
    );

    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(
      'Groups in this group',
    );
    expect(screen.getByText('Everybody in these is in this one.')).toBeTruthy();
  });

  it('links a group to its page', () => {
    render(<GroupLinks title="Part of" groups={[DEVELOPERS]} />);

    const link = screen.getByText('Developers') as HTMLAnchorElement;
    expect(link.tagName).toBe('A');
    expect(link.getAttribute('href')).toBe('/identity-groups/developers');
  });

  it('does not link a group with no page', () => {
    // A stored membership of a group the site holds no entry for.
    render(<GroupLinks title="Part of" groups={[CONTRACTORS]} />);

    expect((screen.getByText('Contractors') as HTMLElement).tagName).toBe(
      'SPAN',
    );
  });

  it('falls back to the id for a group with no title', () => {
    render(
      <GroupLinks title="Part of" groups={[{ ...CONTRACTORS, title: '' }]} />,
    );

    expect(screen.getByText('contractors')).toBeTruthy();
  });

  it('renders nothing for no groups', () => {
    const { container } = render(<GroupLinks title="Part of" groups={[]} />);

    expect(container.innerHTML).toBe('');
  });

  it('carries the class it is given', () => {
    const { container } = render(
      <GroupLinks
        title="Part of"
        groups={[DEVELOPERS]}
        className="identity-group-view__parents"
      />,
    );

    expect(
      container.querySelector('section.identity-group-view__parents'),
    ).toBeTruthy();
  });
});
