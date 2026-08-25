/**
 * A link to the user's own Profile, plugged into Volto's user menu.
 *
 * Only for a user who has one -- which, as :mod:`helpers/profileSource`
 * explains, is the same thing as their fields being held in it.
 *
 * For that user it *replaces* Volto's own Profile link rather than sitting
 * beside it, and takes its name: two entries both called "Profile" make the
 * reader guess which is which, and the content object is where their fields
 * actually live. Taking the slot rather than adding to it is why they share
 * an `order`, and why
 * :func:`~components/UserMenu/UserMenuPlugs.PersonalInformationMenuItem`
 * renders nothing once this one can.
 * @module components/UserMenu/ProfileMenuItem
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Plug } from '@plone/volto/components/manage/Pluggable';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import { profileHoldsTheFields } from '../../helpers/profileSource';
import MenuItem from './MenuItem';

const messages = defineMessages({
  // The same label Volto's own entry carries, because this stands in its
  // place rather than beside it.
  title: { id: 'Profile', defaultMessage: 'Profile' },
});

const ProfileMenuItem: React.FC = () => {
  const intl = useIntl();
  // A primitive, not the user object: `useSelector` compares by identity,
  // and selecting the user whole re-renders this on every store
  // notification.
  const profileUrl = useSelector(
    (state: any) => state.userProfile?.data?.profile_url,
  );

  if (!profileHoldsTheFields(profileUrl)) {
    return null;
  }

  return (
    <Plug
      pluggable="toolbar-user-menu"
      id="identity-profile"
      order={10}
      dependencies={[profileUrl]}
    >
      <MenuItem
        id="toolbar-identity-profile"
        label={intl.formatMessage(messages.title)}
        to={flattenToAppURL(profileUrl)}
      />
    </Plug>
  );
};

export default ProfileMenuItem;
