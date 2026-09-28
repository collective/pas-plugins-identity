import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import ClientsPanel from './ClientsPanel';
import {
  CLIENT_SCHEMA,
  CLIENTS,
  GROUPS_STATE,
  KEYRING,
  MINTED_CLIENT,
  SERVER_SETTINGS,
  UNCONFIGURED_SERVER_SETTINGS,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ClientsPanel> = {
  title: 'Identity/ControlPanel/ClientsPanel',
  component: ClientsPanel,
  args: {
    clients: CLIENTS,
    schema: CLIENT_SCHEMA,
    keys: KEYRING,
    settings: SERVER_SETTINGS,
    loading: false,
    busy: false,
    minted: null,
    view: 'list',
    editing: null,
    formRef: React.createRef(),
    onSubmit: () => {},
    onSaveSettings: () => {},
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
 * store above them. The allowed groups picker reads its vocabulary from
 * it, so one is loaded.
 */
const withForm = withStore({ vocabularies: GROUPS_STATE });

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

/**
 * A client only some people may sign in to: members of the groups picked
 * here, directly or through a nested group.
 */
export const EditingRestricted: Story = {
  args: { view: 'edit', editing: 'stats' },
  decorators: [withForm],
};

/** The ring its tokens are signed with, behind its own toolbar button. */
export const Keys: Story = { args: { view: 'keys' } };

/** A site whose server layer is installed but has never signed anything. */
export const NoKeysYet: Story = { args: { view: 'keys', keys: null } };

/**
 * A server nobody has given an issuer yet: it signs nothing, and says so
 * above the list rather than leaving the discovery document's 503 to.
 */
export const NotConfigured: Story = {
  args: { settings: UNCONFIGURED_SERVER_SETTINGS, clients: [] },
};

/**
 * The server's own settings, behind the toolbar's settings button. The groups
 * picker reads its vocabulary from the store, so one is loaded for it.
 */
export const ServerSettings: Story = {
  args: { view: 'settings' },
  decorators: [withStore({ vocabularies: GROUPS_STATE })],
};

/** Opened before the settings have arrived. */
export const ServerSettingsLoading: Story = {
  args: { view: 'settings', settings: null },
};

/** Opened on a backend that would not serve them. */
export const ServerSettingsUnavailable: Story = {
  args: { view: 'settings', settings: null, settingsFailed: true },
};
