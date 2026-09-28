import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';

import MemberSearch from './MemberSearch';

/**
 * Open the box at a URL.
 *
 * A memory router rather than Storybook's static one, so typing into the box
 * moves a location as it does on a page.
 *
 * @param url The location to render at.
 * @returns The decorator.
 */
function atLocation(url: string) {
  const Decorator = (Story: () => ReactNode) => (
    <MemoryRouter initialEntries={[url]}>{Story()}</MemoryRouter>
  );
  return Decorator;
}

const meta: Meta<typeof MemberSearch> = {
  title: 'Identity/Views/GroupsView/MemberSearch',
  component: MemberSearch,
};
export default meta;

type Story = StoryObj<typeof MemberSearch>;

export const Empty: Story = {
  decorators: [atLocation('/identity-groups/staff')],
};

/** Arrived at through a linked search. */
export const FromTheURL: Story = {
  decorators: [atLocation('/identity-groups/staff?q=alice')],
};
