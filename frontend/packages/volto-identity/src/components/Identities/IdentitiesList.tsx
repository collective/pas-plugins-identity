/**
 * The "your sign-in methods" panel, without store or routing.
 * @module components/Identities/IdentitiesList
 */
import React from 'react';
import type { Identity, LoginProvider } from '../../types';

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
  if (loading) {
    return (
      <div className="identity-identities" role="status">
        Loading your sign-in methods…
      </div>
    );
  }

  return (
    <div className="identity-identities">
      <ul className="identity-identities__list">
        {identities.map((identity) => (
          <li key={identity['@id']} data-provider={identity.provider}>
            <span className="identity-identities__title">{identity.title}</span>
            <span className="identity-identities__subject">
              {identity.subject}
            </span>
            <button
              type="button"
              disabled={busy || !identity.can_unlink}
              // Surfaced: the backend refuses to remove the last way in,
              // and a button that only fails when pressed is worse than one
              // that explains itself.
              title={
                identity.can_unlink
                  ? undefined
                  : 'This is your only way to sign in. Add another first.'
              }
              data-action="unlink"
              onClick={() => onUnlink(identity)}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>

      {identities.length === 0 ? (
        <p className="identity-identities__empty">
          You have no external sign-in methods linked yet.
        </p>
      ) : null}

      {available.length ? (
        <div className="identity-identities__add">
          <h3>Add another</h3>
          <ul>
            {available.map((provider) => (
              <li key={provider.id}>
                <button
                  type="button"
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
          That did not work. Please try again.
        </p>
      ) : null}
    </div>
  );
};

export default IdentitiesList;
