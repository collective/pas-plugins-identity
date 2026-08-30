import type { Meta, StoryObj } from '@storybook/react';

import ConfirmModal from './ConfirmModal';

const meta: Meta<typeof ConfirmModal> = {
  title: 'Identity/ControlPanel/ConfirmModal',
  component: ConfirmModal,
  args: {
    open: true,
    header: 'GitHub',
    content:
      'Deleting this provider removes its configuration. The identities ' +
      'linked through it are account data and are kept.',
    onCancel: () => {},
    onConfirm: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ConfirmModal>;

/** Deleting a provider, which is what this replaced a browser dialog for. */
export const Delete: Story = {};

/** A different verb, for an action that is destructive but is not a delete. */
export const Withdraw: Story = {
  args: {
    header: 'Example App',
    content: 'Example App will no longer have access to your account.',
    confirmLabel: 'Withdraw access',
  },
};

/** Not being asked. */
export const Closed: Story = { args: { open: false } };
