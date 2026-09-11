import React, { useState } from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import ProvidersTable, { DND_LIBRARIES } from './ProvidersTable';
import { inOrder } from '../../helpers/providerOrder';
import {
  CONFIGURED,
  loadLazyLibraries,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ProvidersTable> = {
  title: 'Identity/ControlPanel/ProvidersTable',
  component: ProvidersTable,
  args: {
    providers: CONFIGURED,
    onReorder: () => {},
    onTest: () => {},
    onDelete: () => {},
    onExport: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProvidersTable>;

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
 * The list as a Manager uses it: drag a row by its handle, or focus the
 * handle and move it with the keyboard. The story keeps the order it is
 * given, where the panel would also save it.
 */
export const Default: Story = {
  loaders: [loadDragging],
  decorators: [withDragging],
  render: function Render(args) {
    const [providers, setProviders] = useState(args.providers);
    return (
      <ProvidersTable
        {...args}
        providers={providers}
        onReorder={(ids) => setProviders(inOrder(providers, ids))}
      />
    );
  },
};

/** For somebody who may manage the providers and may not export them. */
export const WithoutExport: Story = {
  args: { onExport: undefined },
  decorators: [withStore({})],
};

/** Before the drag library has loaded: on the server, and for a moment after. */
export const BeforeTheDragLibrary: Story = {
  decorators: [withStore({})],
};
