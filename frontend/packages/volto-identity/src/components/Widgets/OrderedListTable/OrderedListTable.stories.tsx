import React, { useState } from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import OrderedListTable from './OrderedListTable';
import { DND_LIBRARIES } from '../../ControlPanel/ProvidersTable';
import {
  loadLazyLibraries,
  SOCIAL_LINK_SCHEMA,
  SOCIAL_LINKS,
  withStore,
} from '../../../stories/fixtures';

const meta: Meta<typeof OrderedListTable> = {
  title: 'Identity/Widgets/OrderedListTable',
  component: OrderedListTable,
  args: {
    id: 'social_links',
    title: 'Profiles',
    description: 'Where else this person can be found.',
    rows: SOCIAL_LINKS,
    schema: SOCIAL_LINK_SCHEMA,
    columns: ['id', 'title', 'href'],
    onChangeRows: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof OrderedListTable>;

/**
 * Put the loaded drag library in the store.
 *
 * The stories' stores are static and ignore the dispatch that would otherwise
 * deliver it, so the story loads it first.
 */
const withDragging = (
  Story: () => ReactNode,
  { loaded }: { loaded: Record<string, any> },
) => withStore({ lazyLibraries: loaded.lazyLibraries })(Story);

const loadDragging = async () => ({
  lazyLibraries: await loadLazyLibraries(DND_LIBRARIES),
});

/**
 * The table as an editor uses it: drag a row by its handle, edit or delete
 * one, or add one with the button beside the label. The story keeps what it
 * is given, where a form would keep it until saved.
 */
export const Default: Story = {
  loaders: [loadDragging],
  decorators: [withDragging],
  render: function Render(args) {
    const [rows, setRows] = useState(args.rows);
    return <OrderedListTable {...args} rows={rows} onChangeRows={setRows} />;
  },
};

/** Fewer columns than the entry has fields: the dialog still has them all. */
export const SomeColumns: Story = {
  ...Default,
  args: { columns: ['id', 'title'] },
};

/** A list with nothing on it yet. */
export const Empty: Story = {
  ...Default,
  args: { rows: [] },
};

/** While the form cannot be edited. */
export const Disabled: Story = {
  args: { isDisabled: true },
  loaders: [loadDragging],
  decorators: [withDragging],
};

/** Before the drag library has loaded: on the server, and for a moment after. */
export const BeforeTheDragLibrary: Story = {
  decorators: [withStore({})],
};
