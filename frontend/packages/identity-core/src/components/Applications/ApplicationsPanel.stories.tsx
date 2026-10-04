import type { Meta, StoryObj } from '@storybook/react';

import ApplicationsPanel from './ApplicationsPanel';
import { FAILED, GRANTS } from '../../stories/fixtures';

/**
 * The applications a user has authorized.
 *
 * The mirror image of the identities list: that one is what somebody signs
 * in *with*, this is what they signed in *to*.
 */
const meta: Meta<typeof ApplicationsPanel> = {
  title: 'Identity/Applications/ApplicationsPanel',
  component: ApplicationsPanel,
  args: {
    grants: GRANTS,
    loading: false,
    selected: null,
    withdrawing: null,
    onSelect: () => {},
    onWithdraw: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ApplicationsPanel>;

/** The listing: a row per application, scanned rather than read. */
export const Authorized: Story = {};

/** One application on its own, which is where the decision is made. */
export const OneInFull: Story = {
  args: { selected: GRANTS.items[0].client_id },
};

/** The detail view of something that reads nothing but your identity. */
export const OneThatReadsNothing: Story = {
  args: { selected: GRANTS.items[1].client_id },
};

/** An answer somebody opened this page to get. */
export const NothingAuthorized: Story = {
  args: { grants: { ...GRANTS, items: [] } },
};

/**
 * An agreement outlives the registration it was made with: the operator
 * removed the client, the record stayed, and the user can still clear it.
 */
export const AnApplicationThatIsGone: Story = {
  args: {
    grants: {
      ...GRANTS,
      items: [{ ...GRANTS.items[0], registered: false, enabled: false }],
    },
  },
};

/** Disabled by an operator, so it is being refused already. */
export const Disabled: Story = {
  args: {
    grants: { ...GRANTS, items: [{ ...GRANTS.items[0], enabled: false }] },
  },
};

export const Withdrawing: Story = {
  args: { withdrawing: GRANTS.items[0].client_id },
};

/** The same, with the details open. */
export const WithdrawingFromTheDetails: Story = {
  args: {
    selected: GRANTS.items[0].client_id,
    withdrawing: GRANTS.items[0].client_id,
  },
};

export const Loading: Story = { args: { grants: null, loading: true } };

export const Unavailable: Story = {
  args: { grants: null, error: FAILED.error },
};
