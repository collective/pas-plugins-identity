/**
 * The "your sign-in methods" panel, without store or routing.
 * @module components/Identities/IdentitiesList
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import type { Identity, LoginProvider } from '../../types';

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
  onLink: (provider: LoginProvider) => void;
  onUnlink: (identity: Identity) => void;
}

const IdentitiesList: React.FC<IdentitiesListProps> = ({
  identities,
  available,
  loading,
  busy,
  error,
  onLink,
  onUnlink,
}) => {
  const intl = useIntl();

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

      {available.length ? (
        <div className="identity-identities__add">
          <h3>{intl.formatMessage(messages.addAnother)}</h3>
          <ul>
            {available.map((provider) => (
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

      {error ? (
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.failed)}
        </p>
      ) : null}
    </div>
  );
};

export default IdentitiesList;
