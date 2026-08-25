import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import ClientsPanel from './ClientsPanel';
import {
  CLIENTS,
  KEYRING,
  MINTED_CLIENT,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ClientsPanel> = {
  title: 'Identity/ControlPanel/ClientsPanel',
  component: ClientsPanel,
  args: {
    clients: CLIENTS,
    keys: KEYRING,
    loading: false,
    busy: false,
    minted: null,
    view: 'list',
    editing: null,
    formRef: React.createRef(),
    onSubmit: () => {},
    onCancel: () => {},
    onEdit: () => {},
    onRotateSecret: () => {},
    onDelete: () => {},
    onRotateKey: () => {},
    onDismissSecret: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ClientsPanel>;

/**
 * Volto's `Form` is a connected component, so the two form views need a
 * store above them even though this schema asks nothing of it.
 */
const withForm = withStore({});

/** Who may log in *to* this site. The add action lives in the toolbar. */
export const Registered: Story = {};

export const Empty: Story = { args: { clients: [] } };

export const Loading: Story = { args: { loading: true, clients: [] } };

export const Busy: Story = { args: { busy: true } };

/** Straight after registering one: the secret is readable exactly now. */
export const SecretJustMinted: Story = { args: { minted: MINTED_CLIENT } };

/** The registration form, reached from the toolbar's add button. */
export const Registering: Story = {
  args: { view: 'add' },
  decorators: [withForm],
};

/** The same form over a stored client, minus what cannot be changed. */
export const Editing: Story = {
  args: { view: 'edit', editing: CLIENTS[0].client_id },
  decorators: [withForm],
};

/** The ring its tokens are signed with, behind its own toolbar button. */
export const Keys: Story = { args: { view: 'keys' } };

/** A site whose server layer is installed but has never signed anything. */
export const NoKeysYet: Story = { args: { view: 'keys', keys: null } };
