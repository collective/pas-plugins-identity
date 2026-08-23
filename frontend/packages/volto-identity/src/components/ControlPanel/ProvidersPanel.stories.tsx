import type { Meta, StoryObj } from '@storybook/react';

import ProvidersPanel from './ProvidersPanel';
import {
  CONFIGURED,
  DRIVERS,
  USER_FIELDS_STATE,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ProvidersPanel> = {
  title: 'Identity/ControlPanel/ProvidersPanel',
  component: ProvidersPanel,
  // The property-map editor is a Volto form widget and reads the
  // vocabulary from the store.
  decorators: [withStore({ vocabularies: USER_FIELDS_STATE })],
  args: {
    providers: CONFIGURED,
    drivers: DRIVERS,
    loading: false,
    busy: false,
    onCreate: () => {},
    onSave: () => {},
    onDelete: () => {},
    onTest: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProvidersPanel>;

export const Configured: Story = {};

/** A fresh site: nothing configured, and the form that fixes that. */
export const Empty: Story = { args: { providers: [] } };

/** Nothing to configure with, because no add-on registered a driver. */
export const NoDrivers: Story = { args: { providers: [], drivers: [] } };

export const Loading: Story = { args: { loading: true, providers: [] } };

export const Saving: Story = { args: { busy: true } };

export const Checking: Story = { args: { checking: 'keycloak' } };

/** A check that reached the provider and read its discovery document. */
export const CheckPassed: Story = {
  args: {
    check: {
      ok: true,
      authorization_endpoint: 'https://id.example.org/authorize',
      token_endpoint: 'https://id.example.org/token',
      has_jwks: true,
    },
  },
};

/** The failure an operator actually hits: a typo in the issuer. */
export const CheckFailed: Story = {
  args: {
    check: { ok: false, error: 'Discovery returned 404 for that issuer.' },
  },
};
