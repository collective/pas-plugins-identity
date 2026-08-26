import type { Meta, StoryObj } from '@storybook/react';

import EmailLinkForm from './EmailLinkForm';

const meta: Meta<typeof EmailLinkForm> = {
  title: 'Identity/Identities/EmailLinkForm',
  component: EmailLinkForm,
  args: { sent: false, loading: false, onSend: () => {} },
};
export default meta;

type Story = StoryObj<typeof EmailLinkForm>;

export const Default: Story = {};

export const Sending: Story = { args: { loading: true } };

/**
 * Unlike the login page's version, this confirmation may be specific: the
 * reader is signed in and typed the address themselves, so there is nothing
 * to enumerate.
 */
export const Sent: Story = { args: { sent: true } };
