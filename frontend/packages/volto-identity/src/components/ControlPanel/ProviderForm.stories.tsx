import type { Meta, StoryObj } from '@storybook/react';

import ProviderForm from './ProviderForm';
import { OIDC_DRIVER } from '../../stories/fixtures';

const meta: Meta<typeof ProviderForm> = {
  title: 'Identity/ControlPanel/ProviderForm',
  component: ProviderForm,
  args: {
    driver: OIDC_DRIVER,
    values: {
      client_id: 'plone',
      issuer: 'https://id.example.org/realms/main',
      scope: 'openid email profile',
    },
    disabled: false,
    onChange: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProviderForm>;

/** The form is built from the driver's schema, not written per driver. */
export const Empty: Story = { args: { values: {} } };

export const Configured: Story = {};

/**
 * A stored secret comes back masked and can be echoed back unchanged, so the
 * operator never has to retype one to edit something else.
 */
export const WithStoredSecret: Story = {
  args: { values: { client_id: 'plone', client_secret: '••••••••' } },
};

export const Disabled: Story = { args: { disabled: true } };
