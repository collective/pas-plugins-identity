/**
 * Your addresses, and the button that proves one.
 *
 * This is what replaced the free-text box that used to sit on this page. That
 * box asked for an address and mailed a link to it, which verified *any*
 * mailbox somebody could reach -- and a verified address is what a new
 * provider account can be auto-attached to. So the addresses offered here are
 * the ones already on your profile, and adding one is an edit to the profile
 * rather than something this panel does.
 *
 * Verifying is still the same magic link and the same endpoint; what changed
 * is that the backend now refuses an address that is not yours.
 *
 * **Choosing which one is yours.** A provider that knows several of your
 * addresses puts all of them on your profile, so the question is no longer
 * which one to keep but which one stands for you here. That is the *order* of
 * the list -- the backend derives `email` from it, preferring the first
 * verified address -- so {guilabel}`Make preferred` moves one to the front
 * rather than setting a field. An unverified address can be moved and will not
 * win while a verified one is on the list, which is why the badge is what says
 * who won rather than what you last clicked.
 * @module components/Identities/ProfileEmails
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import type { ProfileEmail } from '../../types';

import './ProfileEmails.scss';

const messages = defineMessages({
  heading: {
    id: 'Your email addresses',
    defaultMessage: 'Your email addresses',
  },
  intro: {
    id: 'profile-emails-intro',
    defaultMessage:
      'A verified address can be used to sign in with a link, and to ' +
      'recognise you when you add another provider. Add an address on your ' +
      'profile first, then verify it here.',
  },
  verify: { id: 'Verify', defaultMessage: 'Verify' },
  makePreferred: {
    id: 'Make preferred',
    defaultMessage: 'Make preferred',
  },
  verified: { id: 'Verified', defaultMessage: 'Verified' },
  preferred: { id: 'Preferred', defaultMessage: 'Preferred' },
  preferredHelp: {
    id: 'profile-emails-preferred-help',
    defaultMessage:
      'The address this site uses for you: the first verified one, or the ' +
      'first on your profile when none is verified.',
  },
  choose: {
    id: 'profile-emails-choose',
    defaultMessage:
      'Move an address to the top to make it the one this site uses for you.',
  },
  empty: {
    id: 'profile-emails-empty',
    defaultMessage: 'Your profile carries no email address yet.',
  },
  edit: { id: 'Edit your profile', defaultMessage: 'Edit your profile' },
  sent: {
    id: 'profile-emails-sent',
    defaultMessage:
      'Check that mailbox. The link confirms the address; it does not sign ' +
      'anybody in.',
  },
});

interface ProfileEmailsProps {
  emails: ProfileEmail[];
  /** Where the profile's own edit form is, when the user has a profile. */
  profileUrl?: string | null;
  loading: boolean;
  busy: boolean;
  /** Whether a confirmation mail has just gone out. */
  sent: boolean;
  onVerify: (address: string) => void;
  /**
   * Move an address to the front of the list.
   *
   * Optional so that a page rendering this panel read-only -- or one talking
   * to a backend that predates the reorder -- can leave the buttons out
   * rather than wire up a handler that does nothing.
   */
  onPrefer?: (address: string) => void;
}

const ProfileEmails: React.FC<ProfileEmailsProps> = ({
  emails,
  profileUrl,
  loading,
  busy,
  sent,
  onVerify,
  onPrefer,
}) => {
  const intl = useIntl();

  if (loading) {
    return null;
  }

  return (
    <div className="identity-emails">
      <h3>{intl.formatMessage(messages.heading)}</h3>
      <p className="identity-note">{intl.formatMessage(messages.intro)}</p>
      {onPrefer && emails.length > 1 ? (
        <p className="identity-note">{intl.formatMessage(messages.choose)}</p>
      ) : null}

      {emails.length ? (
        <ul className="identity-emails__list">
          {emails.map((entry) => (
            <li key={entry.address} data-address={entry.address}>
              <span className="identity-emails__address">{entry.address}</span>
              {entry.verified ? (
                <span
                  className="identity-emails__badge identity-emails__badge--verified"
                  data-state="verified"
                >
                  {intl.formatMessage(messages.verified)}
                </span>
              ) : (
                <button
                  type="button"
                  className="identity-button"
                  data-action="verify"
                  disabled={busy}
                  onClick={() => onVerify(entry.address)}
                >
                  {intl.formatMessage(messages.verify)}
                </button>
              )}
              {entry.preferred ? (
                <span
                  className="identity-emails__badge"
                  data-state="preferred"
                  title={intl.formatMessage(messages.preferredHelp)}
                >
                  {intl.formatMessage(messages.preferred)}
                </span>
              ) : null}
              {onPrefer && !entry.preferred ? (
                <button
                  type="button"
                  className="identity-button identity-button--quiet"
                  data-action="prefer"
                  disabled={busy}
                  onClick={() => onPrefer(entry.address)}
                >
                  {intl.formatMessage(messages.makePreferred)}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="identity-note">{intl.formatMessage(messages.empty)}</p>
      )}

      {sent ? (
        <p className="identity-emails__sent" role="status">
          {intl.formatMessage(messages.sent)}
        </p>
      ) : null}

      {profileUrl ? (
        <p className="identity-emails__edit">
          {/* An ordinary link rather than a router push: the profile is
              content, and its edit form is Volto's own. */}
          <a href={`${profileUrl}/edit`}>{intl.formatMessage(messages.edit)}</a>
        </p>
      ) : null}
    </div>
  );
};

export default ProfileEmails;
