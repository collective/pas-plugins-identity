/**
 * The signed-in user, as a picture or as their initials.
 *
 * Reads the user this package keeps in the store rather than Volto's
 * `state.users.user`: that one is fetched when the personal-tools menu opens
 * and cleared around it, and this renders in the toolbar, on every page,
 * whether or not the menu was ever opened.
 *
 * It always renders *something*. A user with no portrait gets initials on a
 * colour derived from their userid; a portrait that fails to load falls back
 * to those initials rather than to a broken-image glyph; a user whose name
 * has not arrived gets the plain circle, which is what the space looked like
 * before.
 * @module components/UserMenu/UserAvatar
 */
import React, { useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import { useIntl, defineMessages } from 'react-intl';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import { colorFor, initialsFor } from '../../helpers/avatar';

import './UserAvatar.scss';

const messages = defineMessages({
  avatar: { id: 'user avatar', defaultMessage: 'user avatar' },
});

export interface UserAvatarProps {
  /** Rendered size, as a CSS length. Square. */
  size?: string;
  /** Extra classes, for a caller that places the avatar itself. */
  className?: string;
}

/**
 * Join the class names for one variant.
 *
 * Deliberately not `classnames`: that is Volto's dependency, not this
 * package's, and this add-on declares no runtime dependencies at all. One
 * `filter` is a smaller price than the first entry in that list.
 *
 * @param variant The variant class, picture or initials.
 * @param extra Whatever the caller passed.
 * @returns The class attribute.
 */
function classes(variant: string, extra?: string): string {
  return ['identity-avatar', variant, extra].filter(Boolean).join(' ');
}

/** The user fields this component reads. */
interface AvatarUser {
  id?: string | null;
  fullname?: string | null;
  portrait?: string | null;
}

const UserAvatar: React.FC<UserAvatarProps> = ({
  size = '30px',
  className,
}) => {
  const intl = useIntl();
  const user = useSelector(
    (state: any) => state.userProfile?.data,
  ) as AvatarUser | null;
  // Keyed by URL so that signing in as somebody else, or uploading a new
  // portrait, gets a fresh attempt rather than inheriting the last failure.
  const [failedPortrait, setFailedPortrait] = useState<string | null>(null);

  const portrait = user?.portrait ?? null;
  const label = intl.formatMessage(messages.avatar);

  // Both walk the name or the userid character by character. Cheap, but this
  // renders on every page in a toolbar that re-renders often.
  const initials = useMemo(
    () => initialsFor(user?.fullname || user?.id),
    [user?.fullname, user?.id],
  );
  const background = useMemo(() => colorFor(user?.id), [user?.id]);

  if (portrait && portrait !== failedPortrait) {
    return (
      <img
        className={classes('identity-avatar--picture', className)}
        style={{ width: size, height: size }}
        src={flattenToAppURL(portrait)}
        alt={label}
        // A portrait that 404s -- deleted, or a stale URL after a rename --
        // would otherwise render as the browser's broken-image glyph, which
        // looks like a bug in the site rather than a missing photograph.
        onError={() => setFailedPortrait(portrait)}
      />
    );
  }

  return (
    <span
      className={classes('identity-avatar--initials', className)}
      style={{
        width: size,
        height: size,
        // Inline because the colour is per user: a class per palette entry
        // would be ten rules that exist only to avoid this attribute.
        backgroundColor: background,
        // The glyph should fill the circle at whatever size it is asked for.
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
