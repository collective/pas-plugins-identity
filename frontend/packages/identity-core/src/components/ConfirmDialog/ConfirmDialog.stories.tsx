import type { Meta, StoryObj } from '@storybook/react';

import ConfirmDialog from './ConfirmDialog';

const meta: Meta<typeof ConfirmDialog> = {
  title: 'Identity/ConfirmDialog',
  component: ConfirmDialog,
  args: {
    isOpen: true,
    title: 'Example App',
    message:
      'Withdraw access for Example App? It will be signed out everywhere and ' +
      'will have to ask you again next time.',
    confirmLabel: 'Withdraw access',
    onConfirm: () => {},
    onCancel: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ConfirmDialog>;

/** Asking before withdrawing an application's access. */
export const Withdraw: Story = {};
