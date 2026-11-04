import type { Meta, StoryObj } from '@storybook/react';

import AddMembers from './AddMembers';
import type { Candidate } from './AddMembers';

const CANDIDATES: Candidate[] = [
  { id: 'developers', title: 'Developers', type: 'group' },
  {
    id: 'alice',
    title: 'Alice Liddell',
    type: 'user',
    detail: 'alice@example.com',
  },
  {
    id: 'alicia',
    title: 'Alicia Florrick',
    type: 'user',
    detail: 'alicia@example.com',
  },
];

const meta: Meta<typeof AddMembers> = {
  title: 'Identity/ManageMembers/AddMembers',
  component: AddMembers,
  args: {
    query: 'ali',
    onQuery: () => {},
    candidates: CANDIDATES,
    searching: false,
    busy: false,
    onAdd: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof AddMembers>;

/** Nothing searched for yet. */
export const Empty: Story = {
  args: { query: '', candidates: [] },
};

/** People and a group found; tick any number of them and add them at once. */
export const Found: Story = {};

export const Searching: Story = {
  args: { searching: true, candidates: [] },
};

export const NothingFound: Story = {
  args: { query: 'zelda', candidates: [] },
};

/** A change being saved: nothing can be picked until it is done. */
export const Saving: Story = {
  args: { busy: true },
};
