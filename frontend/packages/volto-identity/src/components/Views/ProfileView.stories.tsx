import type { Meta, StoryObj } from '@storybook/react';

import ProfileView from './ProfileView';
import { PORTRAIT, profileContent } from '../../stories/fixtures';

const CONTENT = profileContent({
  '@id': '/identity-profiles/erico',
  id: 'erico',
  login: 'erico@plone.org',
  fullname: 'Érico Andrei',
  description: 'Plone developer, and the person this add-on is written for.',
  image: { download: PORTRAIT, scales: { preview: { download: PORTRAIT } } },
});

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

/** No full name yet, so the heading is the login the person signs in with. */
export const WithoutAName: Story = {
  args: {
    content: { ...CONTENT, fullname: '', description: '', image: null },
  },
};
