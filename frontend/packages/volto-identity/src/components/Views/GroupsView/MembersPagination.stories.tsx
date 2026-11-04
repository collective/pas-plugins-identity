import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter, useLocation } from 'react-router-dom';

import MembersPagination from './MembersPagination';

/** Show where the pagination has sent the reader, below it. */
const Location = () => {
  const { search } = useLocation();
  return <p className="identity-note">URL: {search || '(no query)'}</p>;
};

/**
 * Open the story at a URL, in a router that follows clicks.
 *
 * @param url Where the story starts, `?page=` included.
 * @returns A Storybook decorator.
 */
const at = (url: string) => (Story: () => ReactNode) => (
  <MemoryRouter initialEntries={[url]}>
    {Story()}
    <Location />
  </MemoryRouter>
);

const meta: Meta<typeof MembersPagination> = {
  title: 'Identity/Views/GroupsView/MembersPagination',
  component: MembersPagination,
  args: { total: 95 },
  decorators: [at('/identity-profiles/staff')],
};
export default meta;

type Story = StoryObj<typeof MembersPagination>;

/** No `?page=`: the first of ten pages. */
export const FirstPage: Story = {};

export const MiddlePage: Story = {
  decorators: [at('/identity-profiles/staff?page=5')],
};

export const LastPage: Story = {
  decorators: [at('/identity-profiles/staff?page=10')],
};

/** Paging a search keeps the search. */
export const WithinASearch: Story = {
  args: { total: 23 },
  decorators: [at('/identity-profiles/staff?q=li&page=2')],
};

/** Two pages only. */
export const TwoPages: Story = {
  args: { total: 11 },
};

/** One page holds everybody, so there is nothing to draw. */
export const OnePage: Story = {
  args: { total: 10 },
};
