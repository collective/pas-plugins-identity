/**
 * The signed-in user, as a picture or as their initials.
 *
 * Reads the user this package keeps in the store rather than Volto's
 * `state.users.user`: that one is fetched when the personal-tools menu opens
 * and cleared around it, and this renders in the toolbar, on every page,
 * whether or not the menu was ever opened.
 *
 * Falls back to whatever it has. A user with no portrait gets initials on a
 * colour derived from their userid; a user whose name has not loaded yet gets
 * the plain circle, which is what the space looked like before.
 * @module components/UserMenu/UserAvatar
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { useIntl, defineMessages } from 'react-intl';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import { colorFor, initialsFor } from '../../helpers/avatar';

import './UserAvatar.scss';

const messages = defineMessages({
  avatar: { id: 'user avatar', defaultMessage: 'user avatar' },
});

interface UserAvatarProps {
  /** Rendered size, as a CSS length. */
  size?: string;
}

const UserAvatar: React.FC<UserAvatarProps> = ({ size = '30px' }) => {
  const intl = useIntl();
  const user = useSelector((state: any) => state.userProfile?.data);

  const portrait = user?.portrait;
  const initials = initialsFor(user?.fullname || user?.id);
  const label = intl.formatMessage(messages.avatar);

  if (portrait) {
    return (
      <img
        className="identity-avatar identity-avatar--picture"
        style={{ width: size, height: size }}
        src={flattenToAppURL(portrait)}
        alt={label}
      />
    );
  }

  return (
    <span
      className="identity-avatar identity-avatar--initials"
      style={{
        width: size,
        height: size,
        // Inline because the colour is per user: a class per palette entry
        // would be ten rules that exist only to avoid this attribute.
        backgroundColor: colorFor(user?.id),
        // The glyph should fill the circle at any size it is asked for.
        fontSize: `calc(${size} / 2.4)`,
      }}
      // Decorative when there are no initials to read: an empty circle
      // announced as "user avatar" is noise to a screen reader.
      role={initials ? 'img' : undefined}
      aria-label={initials ? label : undefined}
      aria-hidden={initials ? undefined : true}
    >
      {initials}
    </span>
  );
};

export default UserAvatar;
