import type { Meta, StoryObj } from '@storybook/react';

import ClientsPanel from './ClientsPanel';
import { CLIENTS, KEYRING, MINTED_CLIENT } from '../../stories/fixtures';

const meta: Meta<typeof ClientsPanel> = {
  title: 'Identity/ControlPanel/ClientsPanel',
  component: ClientsPanel,
  args: {
    clients: CLIENTS,
    keys: KEYRING,
    loading: false,
    busy: false,
    minted: null,
    onCreate: () => {},
    onToggle: () => {},
    onRotateSecret: () => {},
    onDelete: () => {},
    onRotateKey: () => {},
    onDismissSecret: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ClientsPanel>;

/** Who may log in *to* this site, and the ring its tokens are signed with. */
export const Registered: Story = {};

export const Empty: Story = { args: { clients: [] } };

export const Loading: Story = { args: { loading: true, clients: [] } };

export const Busy: Story = { args: { busy: true } };

/** Straight after registering one: the secret is readable exactly now. */
export const SecretJustMinted: Story = { args: { minted: MINTED_CLIENT } };

/** A site whose server layer is installed but has never signed anything. */
export const NoKeysYet: Story = { args: { keys: null } };
