/**
 * The OAuth client control panel, without store or routing.
 * @module components/ControlPanel/ClientsPanel
 */
import React, { useState } from 'react';
import type { OAuthClient, SigningKeyRing } from '../../types';
import SecretReveal from './SecretReveal';

interface ClientsPanelProps {
  clients: OAuthClient[];
  keys: SigningKeyRing | null;
  loading: boolean;
  busy: boolean;
  /** The client whose secret was just minted, if any. */
  minted: OAuthClient | null;
  onCreate: (data: Record<string, unknown>) => void;
  onToggle: (clientId: string, enabled: boolean) => void;
  onRotateSecret: (clientId: string) => void;
  onDelete: (clientId: string) => void;
  onRotateKey: () => void;
  onDismissSecret: () => void;
}

/** A registration form's starting state. */
const BLANK = {
  client_id: '',
  title: '',
  redirect_uris: '',
  scope: '',
  public: false,
};

const ClientsPanel: React.FC<ClientsPanelProps> = ({
  clients,
  keys,
  loading,
  busy,
  minted,
  onCreate,
  onToggle,
  onRotateSecret,
  onDelete,
  onRotateKey,
  onDismissSecret,
}) => {
  const [draft, setDraft] = useState({ ...BLANK });

  if (loading) {
    return (
      <div className="identity-clients" role="status">
        Loading clients…
      </div>
    );
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    onCreate({
      client_id: draft.client_id.trim(),
      title: draft.title.trim(),
      // One per line is what an operator can paste from a provider's own
      // configuration screen. Matching is exact on the backend, so blank
      // lines and stray whitespace have to go.
      redirect_uris: draft.redirect_uris
        .split('\n')
        .map((uri) => uri.trim())
        .filter(Boolean),
      scope: draft.scope.trim(),
      public: draft.public,
    });
    setDraft({ ...BLANK });
  };

  return (
    <div className="identity-clients">
      {minted ? (
        <SecretReveal client={minted} onDismiss={onDismissSecret} />
      ) : null}

      <section className="identity-clients__list">
        <h2>Registered clients</h2>
        {clients.length ? (
          <ul>
            {clients.map((client) => (
              <li key={client['@id']} data-client={client.client_id}>
                <h3>
                  {client.title || client.client_id}{' '}
                  <small>
                    <code>{client.client_id}</code>
                  </small>
                </h3>
                <dl>
                  <dt>Type</dt>
                  <dd>
                    {client.public ? 'Public (PKCE required)' : 'Confidential'}
                  </dd>
                  <dt>Grants</dt>
                  <dd>{client.grant_types.join(', ') || '—'}</dd>
                  <dt>Redirect URIs</dt>
                  <dd>{client.redirect_uris.join(', ') || '—'}</dd>
                  <dt>Scope</dt>
                  <dd>{client.scope || '—'}</dd>
                </dl>
                <div className="identity-clients__actions">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onToggle(client.client_id, !client.enabled)}
                  >
                    {client.enabled ? 'Disable' : 'Enable'}
                  </button>
                  {client.public ? null : (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onRotateSecret(client.client_id)}
                    >
                      Rotate secret
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onDelete(client.client_id)}
                  >
                    Unregister
                  </button>
                </div>
                {client.enabled ? null : (
                  <p className="identity-clients__disabled" role="status">
                    Disabled. Its existing access tokens are refused as well:
                    the audience is checked against this registry on every
                    request.
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="identity-clients__empty">
            No clients are registered yet.
          </p>
        )}
      </section>

      <section className="identity-clients__new">
        <h2>Register a client</h2>
        <form onSubmit={submit}>
          <label>
            Client ID
            <input
              type="text"
              required
              value={draft.client_id}
              onChange={(event) =>
                setDraft({ ...draft, client_id: event.target.value })
              }
            />
          </label>
          <label>
            Title
            <input
              type="text"
              value={draft.title}
              onChange={(event) =>
                setDraft({ ...draft, title: event.target.value })
              }
            />
          </label>
          <label>
            Redirect URIs
            <textarea
              rows={3}
              value={draft.redirect_uris}
              onChange={(event) =>
                setDraft({ ...draft, redirect_uris: event.target.value })
              }
            />
            <small>
              One per line. Matched exactly — a trailing slash or an extra query
              parameter is a different URI.
            </small>
          </label>
          <label>
            Scope
            <input
              type="text"
              value={draft.scope}
              onChange={(event) =>
                setDraft({ ...draft, scope: event.target.value })
              }
            />
            <small>Space separated, for example “openid profile email”.</small>
          </label>
          <label>
            <input
              type="checkbox"
              checked={draft.public}
              onChange={(event) =>
                setDraft({ ...draft, public: event.target.checked })
              }
            />
            Public client
            <small>
              A browser or native app, which cannot keep a secret. PKCE is
              required for these and no secret is issued.
            </small>
          </label>
          <button type="submit" disabled={busy}>
            Register
          </button>
        </form>
      </section>

      <section className="identity-clients__keys">
        <h2>Signing keys</h2>
        {keys ? (
          <>
            <p>
              {keys.items_total} of {keys.ring_size} in the ring, signing with{' '}
              {keys.algorithm}. Public keys are published at{' '}
              <a href={keys.jwks_uri}>{keys.jwks_uri}</a>.
            </p>
            <ul>
              {keys.items.map((key) => (
                <li key={key.kid} data-kid={key.kid}>
                  <code>{key.kid}</code>
                  {key.active ? (
                    <strong> — signing</strong>
                  ) : (
                    ' — verifying only'
                  )}
                </li>
              ))}
            </ul>
            <button type="button" disabled={busy} onClick={onRotateKey}>
              Rotate signing key
            </button>
            <p className="identity-clients__keys-warning">
              Older keys stay in the ring so tokens already issued keep
              verifying. The ring holds {keys.ring_size}; rotating more than
              that within one access-token lifetime will invalidate tokens still
              in flight.
            </p>
          </>
        ) : (
          <p role="status">Loading keys…</p>
        )}
      </section>
    </div>
  );
};

export default ClientsPanel;
