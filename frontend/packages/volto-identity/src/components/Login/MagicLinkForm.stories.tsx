import type { Meta, StoryObj } from '@storybook/react';

import MagicLinkForm from './MagicLinkForm';
import { FAILED, withLoginCard } from '../../stories/fixtures';

const meta: Meta<typeof MagicLinkForm> = {
  title: 'Identity/Login/MagicLinkForm',
  component: MagicLinkForm,
  decorators: [withLoginCard()],
  args: { sent: false, loading: false, onSend: () => {} },
};
export default meta;

type Story = StoryObj<typeof MagicLinkForm>;

export const Default: Story = {};

export const Sending: Story = { args: { loading: true } };

/**
 * The confirmation says nothing about whether the address is known: the
 * backend answers identically either way, and a UI that distinguished them
 * would undo that.
 */
export const Sent: Story = { args: { sent: true } };

export const Failed: Story = { args: { error: FAILED.error } };
