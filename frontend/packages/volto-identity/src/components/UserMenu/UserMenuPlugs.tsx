/**
 * Volto's own personal-tools entries, re-registered as plugs.
 *
 * The menu used to be three entries written into `PersonalTools` plus a
 * pluggable at the end, which meant an add-on could only ever *append*: a
 * site wanting "Sign-in methods" under "Preferences", or wanting no "Site
 * Setup" link, had to shadow the component again. Here every entry is a plug
 * with an `order`, including the ones Volto ships, so the whole menu is one
 * ordered list a site composes rather than three fixed things and a bucket.
 *
 * The orders are spaced by ten, so an add-on can land between two of them
 * without renumbering anything:
 *
 * ==== ==========================================================
 *   10 The profile -- this package's, when the user has one;
 *      Volto's member form otherwise. Never both: see below.
 *   20 Preferences
 *   30 Sign-in methods, which is asked for right after preferences
 *      because it *is* a preference: it is where a person adds or
 *      drops a way of getting in.
 *   35 Applications, on a site running the `[server]` layer -- the
 *      same question the other way round, so it sits next to it.
 *      A number between two of these is exactly what the spacing
 *      is for.
 *   40 Site Setup, for a manager. Last because it is about the
 *      site rather than about the person.
 * ==== ==========================================================
 *
 * `loadComponent` reaches these through the pluggable's `params`, which is
 * how a plug rendered from `appExtras` gets at a prop that belongs to
 * `PersonalTools`. A plug that needs it takes a function child; one that does
 * not takes plain children and never sees them.
 * @module components/UserMenu/UserMenuPlugs
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Plug } from '@plone/volto/components/manage/Pluggable';

import { profileHoldsTheFields } from '../../helpers/profileSource';
import MenuItem from './MenuItem';

const messages = defineMessages({
  preferences: { id: 'Preferences', defaultMessage: 'Preferences' },
  profile: { id: 'Profile', defaultMessage: 'Profile' },
  siteSetup: { id: 'Site Setup', defaultMessage: 'Site Setup' },
});

/** Params the personal-tools pluggable hands to every plug. */
export interface UserMenuParams {
  /** Slide another panel into the toolbar, by its registered name. */
  loadComponent: (selector: string) => void;
}

/**
 * Volto's own Profile entry, which is the member form at
 * `/personal-information`.
 *
 * Absent for a user whose fields are held in a Profile, where
 * `ProfileMenuItem` takes this slot under the same name. It keeps the slot
 * on a site without the `[content]` layer and for a user first login has not
 * minted a Profile for -- who are exactly the users whose fields really are
 * edited at `/personal-information`.
 */
export const PersonalInformationMenuItem: React.FC = () => {
  const intl = useIntl();
  // A primitive; see `ProfileMenuItem` for why.
  const profileUrl = useSelector(
    (state: any) => state.userProfile?.data?.profile_url,
  );

  if (profileHoldsTheFields(profileUrl)) {
    return null;
  }

  return (
    <Plug
      pluggable="toolbar-user-menu"
      id="personal-information"
      order={10}
      dependencies={[profileUrl]}
    >
      <MenuItem
        id="toolbar-profile"
        label={intl.formatMessage(messages.profile)}
        to="/personal-information"
      />
    </Plug>
  );
};

/** Volto's Preferences panel, which slides in rather than being a route. */
export const PreferencesMenuItem: React.FC = () => {
  const intl = useIntl();
  return (
    <Plug pluggable="toolbar-user-menu" id="preferences" order={20}>
      {({ loadComponent }: UserMenuParams) => (
        <MenuItem
          id="toolbar-preferences"
          label={intl.formatMessage(messages.preferences)}
          onClick={() => loadComponent('preferences')}
        />
      )}
    </Plug>
  );
};

/**
 * Volto's Site Setup link, for a user who may see it.
 *
 * The condition is upstream's: the `plone_setup` user action, which the
 * backend only lists for somebody allowed to reach the control panels. Read
 * from the store here rather than passed through `params`, so this plug does
 * not need `PersonalTools` to know about it.
 */
export const SiteSetupMenuItem: React.FC = () => {
  const intl = useIntl();
  const siteSetupAction = useSelector((state: any) =>
    state.actions?.actions?.user?.find(
      (action: { id?: string }) => action?.id === 'plone_setup',
    ),
  );

  if (!siteSetupAction) {
    return null;
  }

  return (
    <Plug
      pluggable="toolbar-user-menu"
      id="site-setup"
      order={40}
      dependencies={[Boolean(siteSetupAction)]}
    >
      <MenuItem
        id="toolbar-site-setup"
        label={intl.formatMessage(messages.siteSetup)}
        to="/controlpanel"
      />
    </Plug>
  );
};
