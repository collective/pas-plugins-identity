import type { Meta, StoryObj } from '@storybook/react';

import PersonalTools from './PersonalTools';
import { withToolbar } from '../../stories/withUserMenu';
import { LOADED, USER, withStore } from '../../stories/fixtures';

/**
 * The shadowed personal-tools menu.
 *
 * Its entries are the `personal_tools` actions the backend lists for the
 * user, so each story is the payload one kind of user receives from this
 * package's profile.
 *
 * The menu is normally sized to the toolbar it slides over, which is not
 * here -- `theToolbar` is an empty ref, so it takes its natural width.
 */
const meta: Meta<typeof PersonalTools> = {
  title: 'Identity/UserMenu/PersonalTools',
  component: PersonalTools,
  // It renders `.personal-tools.pastanaga-menu` itself, but every rule for
  // that class is nested under `#toolbar` in `toolbar.less` -- so without
  // this ancestor the menu came out as an unstyled column of links.
  decorators: [withToolbar],
  parameters: { fullBleed: true },
  args: {
    loadComponent: () => {},
    unloadComponent: () => {},
    theToolbar: { current: null },
  },
};
export default meta;

type Story = StoryObj<typeof PersonalTools>;

const PROFILE_FORM = {
  id: 'profile',
  title: 'Profile',
  url: '/personal-information',
};
const IDENTITY_PROFILE = {
  id: 'identity_profile',
  title: 'Profile',
  url: '/identity-profiles/alice',
};
const PREFERENCES = {
  id: 'preferences',
  title: 'Preferences',
  url: 'preferences',
};
const IDENTITIES = {
  id: 'identities',
  title: 'Sign-in methods',
  url: '/identities',
};
const APPLICATIONS = {
  id: 'applications',
  title: 'Applications',
  url: '/applications',
};
const SITE_SETUP = {
  id: 'plone_setup',
  title: 'Site Setup',
  url: '/controlpanel',
};

const withState = (
  user: Record<string, unknown>,
  personalTools: unknown[] | undefined,
) =>
  withStore({
    userProfile: { ...LOADED, data: { ...USER, ...user } },
    actions: { actions: { personal_tools: personalTools, user: [] } },
  });

/** A member with a Profile: the Profile takes the first slot. */
export const Member: Story = {
  decorators: [withState({}, [IDENTITY_PROFILE, PREFERENCES, IDENTITIES])],
};

/**
 * A manager on a site running the authorization server: Applications, then
 * Site Setup, last because it is about the site.
 */
export const Manager: Story = {
  decorators: [
    withState({}, [
      IDENTITY_PROFILE,
      PREFERENCES,
      IDENTITIES,
      APPLICATIONS,
      SITE_SETUP,
    ]),
  ],
};

/**
 * A user with no Profile: Volto's own Profile link takes the slot, leading
 * to the member form at `/personal-information`.
 */
export const WithoutAProfile: Story = {
  decorators: [
    withState({ profile_url: null }, [PROFILE_FORM, PREFERENCES, IDENTITIES]),
  ],
};

/**
 * A backend without the `personal_tools` actions: Volto's built-in entries,
 * as Volto itself falls back to.
 */
export const WithoutTheActions: Story = {
  decorators: [withState({}, undefined)],
};

/**
 * A user with no name yet. The header shows the userid rather than nothing:
 * an empty header reads as a broken menu.
 */
export const NameNotLoadedYet: Story = {
  decorators: [
    withState({ fullname: null, username: null }, [
      IDENTITY_PROFILE,
      PREFERENCES,
      IDENTITIES,
    ]),
  ],
};
