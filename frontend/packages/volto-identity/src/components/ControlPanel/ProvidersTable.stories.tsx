import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import ProvidersTable from './ProvidersTable';
import { inOrder } from '../../helpers/providerOrder';
import { CONFIGURED } from '../../stories/fixtures';

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
 * The list as a Manager uses it: drag a row by its handle, or focus the
 * handle and move it with the keyboard. The story keeps the order it is
 * given, where the panel would also save it.
 */
export const Default: Story = {
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
};
