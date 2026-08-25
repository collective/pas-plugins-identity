/**
 * A link to the user's own Profile, plugged into Volto's user menu.
 *
 * Only on a site running the `[profile]` layer, and only once first login has
 * minted one: `profile_url` is null otherwise, and an entry leading nowhere
 * is worse than no entry. It sits beside Volto's own "Profile" link rather
 * than replacing it -- that one goes to `/personal-information`, the form for
 * editing your own member fields, which is a different thing from the Profile
 * content object this add-on files you under.
 * @module components/UserMenu/ProfileMenuItem
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import { Plug } from '@plone/volto/components/manage/Pluggable';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';

const messages = defineMessages({
  title: { id: 'My profile', defaultMessage: 'My profile' },
});

const ProfileMenuItem: React.FC = () => {
  const intl = useIntl();
  const profileUrl = useSelector(
    (state: any) => state.userProfile?.data?.profile_url,
  );

  if (!profileUrl) {
    return null;
  }

  return (
    <Plug pluggable="toolbar-user-menu" id="identity-profile">
      <li>
        <Link id="toolbar-identity-profile" to={flattenToAppURL(profileUrl)}>
          {intl.formatMessage(messages.title)}
          <Icon name={rightArrowSVG} size="24px" />
        </Link>
      </li>
    </Plug>
  );
};

export default ProfileMenuItem;
