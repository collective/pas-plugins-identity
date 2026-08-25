import type { Meta, StoryObj } from '@storybook/react';

import ConsentPanel from './ConsentPanel';
import { CONSENT_REQUEST, FAILED } from '../../stories/fixtures';

/**
 * The consent screen.
 *
 * The reason it is a Volto route at all: a relying party sent this browser
 * here to be asked something personal, and a screen that looks nothing like
 * the site the person thinks they are signing in to is the screen they should
 * not trust.
 */
const meta: Meta<typeof ConsentPanel> = {
  title: 'Identity/Consent/ConsentPanel',
  component: ConsentPanel,
  args: {
    request: CONSENT_REQUEST,
    loading: false,
    answering: false,
    onAnswer: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ConsentPanel>;

export const Asking: Story = {};

/** `openid` alone: an identity, and nothing else released. */
export const NothingReleased: Story = {
  args: {
    request: { ...CONSENT_REQUEST, scopes: [{ id: 'openid', claims: [] }] },
  },
};

/** A client asking for everything this server publishes. */
export const EverythingReleased: Story = {
  args: {
    request: {
      ...CONSENT_REQUEST,
      scopes: [
        { id: 'openid', claims: [] },
        {
          id: 'profile',
          claims: [
            'name',
            'preferred_username',
            'website',
            'picture',
            'description',
          ],
        },
        { id: 'email', claims: ['email', 'email_verified'] },
        { id: 'address', claims: ['address'] },
      ],
    },
  },
};

/** A client registered without a title is named by its id. */
export const AnUntitledClient: Story = {
  args: {
    request: { ...CONSENT_REQUEST, client: { id: 'app', title: 'app' } },
  },
};

export const Loading: Story = { args: { request: null, loading: true } };

/** The answer is on its way and the browser is leaving. */
export const Answering: Story = { args: { answering: true } };

/**
 * A request this server would not honour: an unknown client, or a redirect
 * URI that matches nothing registered. No buttons — an "Allow" here would be
 * agreeing to something the page could not describe.
 */
export const Unavailable: Story = {
  args: { request: null, error: FAILED.error },
};
