import type { Meta, StoryObj } from '@storybook/react';

import ProviderButton from './ProviderButton';
import { GITHUB, GOOGLE, KEYCLOAK } from '../../stories/fixtures';

const meta: Meta<typeof ProviderButton> = {
  title: 'Identity/Login/ProviderButton',
  component: ProviderButton,
  args: { provider: GOOGLE, disabled: false, onSelect: () => {} },
};
export default meta;

type Story = StoryObj<typeof ProviderButton>;

export const Google: Story = {};

export const GitHub: Story = { args: { provider: GITHUB } };

/** Any provider reached through discovery, which is most of them. */
export const GenericOIDC: Story = { args: { provider: KEYCLOAK } };

/**
 * Disabled while a redirect is already under way: a second click would start
 * a second flow whose state replaces the first one's.
 */
export const Redirecting: Story = { args: { disabled: true } };

/** A provider whose title the operator never set falls back to its id. */
export const Untitled: Story = {
  args: { provider: { ...GOOGLE, title: '' } },
};
