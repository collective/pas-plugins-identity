/**
 * What a user's Profile looks like when somebody opens it.
 *
 * A Profile is content, so without a view of its own it rendered through
 * Volto's default: a title, and a body that is empty because a Profile has no
 * rich text. What a person visiting one wants is the three things that say who
 * this is -- their name, what they say about themselves, and their picture.
 *
 * Deliberately not the address. The `email` field carries a read permission
 * of its own (`...content.viewpii`), so it is absent from the serialization
 * for most callers anyway -- but a view that rendered it when it happened to
 * be there would publish an address on a page whose URL is guessable from a
 * userid. The account's own owner sees their addresses on their sign-in
 * methods page, where verifying one is also possible.
 * @module components/Views/ProfileView
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import { Container } from 'semantic-ui-react';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import './ProfileView.scss';

const messages = defineMessages({
  noName: { id: 'profile-view-unnamed', defaultMessage: 'Unnamed user' },
});

/** The shape of the fields this view reads off a serialized Profile. */
interface ProfileContent {
  '@id': string;
  title?: string;
  fullname?: string;
  description?: string;
  image?: {
    download?: string;
    scales?: Record<string, { download?: string }>;
  } | null;
}

interface ProfileViewProps {
  content: ProfileContent;
}

/**
 * Return the best available URL for a Profile's picture.
 *
 * A scale rather than the original when there is one: an uploaded portrait
 * is whatever the camera produced, and a page that renders it at full size
 * downloads several megabytes to draw a thumbnail.
 *
 * @param image The serialized image field.
 * @returns The URL, or null when the Profile has no picture.
 */
export function pictureUrl(image: ProfileContent['image']): string | null {
  if (!image) {
    return null;
  }
  return (
    image.scales?.preview?.download ??
    image.scales?.mini?.download ??
    image.download ??
    null
  );
}

const ProfileView: React.FC<ProfileViewProps> = ({ content }) => {
  const intl = useIntl();
  // `title` is computed on the backend from the full name, falling back to
  // the login -- so it is never empty, and it is the honest thing to fall
  // back to before preferring a message of our own.
  const name =
    content.fullname || content.title || intl.formatMessage(messages.noName);
  const picture = pictureUrl(content.image);

  return (
    <Container className="view-wrapper identity-profile-view">
      <Helmet title={name} />
      <div className="identity-profile-view__header">
        {picture ? (
          <img
            className="identity-profile-view__picture"
            src={picture}
            // The name, not "portrait of": a screen reader announcing the
            // word twice on a page whose heading is already the name adds
            // nothing.
            alt={name}
          />
        ) : null}
        <h1 className="documentFirstHeading">{name}</h1>
      </div>
      {content.description ? (
        <p className="documentDescription">{content.description}</p>
      ) : null}
    </Container>
  );
};

export default ProfileView;
