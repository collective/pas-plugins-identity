import type { Meta, StoryObj } from '@storybook/react';

import ProfileView from './ProfileView';
import { PORTRAIT } from '../../stories/fixtures';

const CONTENT = {
  '@id': '/identity-profiles/erico',
  title: 'Érico Andrei',
  fullname: 'Érico Andrei',
  description: 'Plone developer, and the person this add-on is written for.',
  image: { download: PORTRAIT, scales: { preview: { download: PORTRAIT } } },
};

const meta: Meta<typeof ProfileView> = {
  title: 'Identity/Views/ProfileView',
  component: ProfileView,
  args: { content: CONTENT },
};
export default meta;

type Story = StoryObj<typeof ProfileView>;

/** Everything filled in: a name, a biography and a picture. */
export const Complete: Story = {};

/** No picture. The page is the name and what they said about themselves. */
export const WithoutAPicture: Story = {
  args: { content: { ...CONTENT, image: null } },
};

/** A profile minted at first login by a provider that sent only a name. */
export const JustCreated: Story = {
  args: { content: { ...CONTENT, description: '', image: null } },
};
