import { describe, expect, it } from 'vitest';
import { render } from '../../../testing';
import React from 'react';

import MembersCount from './MembersCount';

/**
 * Render the counts and read them back as a reader would.
 *
 * @param total Everybody in the group.
 * @param direct The direct members.
 * @returns The text of each count, in order.
 */
function counts(total: number, direct: number): string[] {
  const { container } = render(<MembersCount total={total} direct={direct} />);
  return Array.from(
    container.querySelectorAll('.identity-members-count > .identity-count'),
  ).map((node) => node.textContent ?? '');
}

describe('MembersCount', () => {
  it('says how many people are in the group', () => {
    expect(counts(42, 12)[0]).toBe('42 members');
  });

  it('says one member rather than one members', () => {
    expect(counts(1, 1)).toEqual(['1 member']);
  });

  it('splits the count when some came through a nested group', () => {
    expect(counts(42, 12)).toEqual([
      '42 members',
      '12 directly',
      '30 through nested groups',
    ]);
  });

  it('does not split it when everybody is a direct member', () => {
    expect(counts(8, 8)).toEqual(['8 members']);
  });

  it('sets the split back behind the total', () => {
    const { container } = render(<MembersCount total={42} direct={12} />);

    const secondary = container.querySelectorAll('.identity-count--secondary');
    expect(secondary).toHaveLength(2);
  });
});
