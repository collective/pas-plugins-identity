/**
 * The "your sign-in methods" panel, without store or routing.
 * @module components/Identities/IdentitiesList
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import type { Identity, LoginProvider } from '../../types';
import { splitLinkable } from '../../helpers/identities';
import EmailLinkForm from './EmailLinkForm';

import './IdentitiesList.scss';

const messages = defineMessages({
  loading: {
    id: 'Loading your sign-in methods',
    defaultMessage: 'Loading your sign-in methods…',
  },
  remove: { id: 'Remove', defaultMessage: 'Remove' },
  lastWayIn: {
    id: 'This is your only way to sign in. Add another first.',
    defaultMessage: 'This is your only way to sign in. Add another first.',
  },
  empty: {
    id: 'You have no external sign-in methods linked yet.',
    defaultMessage: 'You have no external sign-in methods linked yet.',
  },
  addAnother: { id: 'Add another', defaultMessage: 'Add another' },
  failed: {
    id: 'That did not work. Please try again.',
    defaultMessage: 'That did not work. Please try again.',
  },
});

interface IdentitiesListProps {
  identities: Identity[];
  /** Providers that could still be added, already filtered by the caller. */
  available: LoginProvider[];
  loading: boolean;
  busy: boolean;
  error?: unknown;
  /** Whether a confirmation mail has gone out for the email provider. */
  emailSent: boolean;
  onLink: (provider: LoginProvider) => void;
  onLinkEmail: (provider: LoginProvider, email: string) => void;
  onUnlink: (identity: Identity) => void;
}

const IdentitiesList: React.FC<IdentitiesListProps> = ({
  identities,
  available,
  loading,
  busy,
  error,
  emailSent,
  onLink,
  onLinkEmail,
  onUnlink,
}) => {
  const intl = useIntl();
  // Not every provider is a button. The email one proves a mailbox, which
  // means asking which mailbox first -- rendering it as a button posted a
  // link request for a provider with no authorize URL, and the page died on
  // the refusal.
  const { redirect, email } = splitLinkable(available);

  if (loading) {
    return (
      <div className="identity-identities" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }

  return (
    <div className="identity-identities">
      <ul className="identity-identities__list">
        {identities.map((identity) => (
          <li key={identity['@id']} data-provider={identity.provider}>
            <span className="identity-identities__title">{identity.title}</span>
            <span className="identity-identities__subject identity-note">
              {identity.subject}
            </span>
            <button
              type="button"
              className="identity-button identity-button--danger"
              disabled={busy || !identity.can_unlink}
              // Surfaced: the backend refuses to remove the last way in,
              // and a button that only fails when pressed is worse than one
              // that explains itself.
              title={
                identity.can_unlink
                  ? undefined
                  : intl.formatMessage(messages.lastWayIn)
              }
              data-action="unlink"
              onClick={() => onUnlink(identity)}
            >
              {intl.formatMessage(messages.remove)}
            </button>
          </li>
        ))}
      </ul>

      {identities.length === 0 ? (
        <p className="identity-identities__empty identity-note">
          {intl.formatMessage(messages.empty)}
        </p>
      ) : null}

      {redirect.length ? (
        <div className="identity-identities__add">
          <h3>{intl.formatMessage(messages.addAnother)}</h3>
          <ul>
            {redirect.map((provider) => (
              <li key={provider.id}>
                <button
                  type="button"
                  className="identity-button"
                  data-provider={provider.id}
                  disabled={busy}
                  onClick={() => onLink(provider)}
                >
                  {provider.title || provider.id}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {email ? (
        <EmailLinkForm
          sent={emailSent}
          loading={busy}
          onSend={(address) => onLinkEmail(email, address)}
        />
      ) : null}

      {error ? (
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.failed)}
        </p>
      ) : null}
    </div>
  );
};

export default IdentitiesList;
