/**
 * The OAuth client control panel, without store or routing.
 * @module components/ControlPanel/ClientsPanel
 */
import React, { useState } from 'react';
import { FormattedMessage, defineMessages, useIntl } from 'react-intl';

import type { OAuthClient, SigningKeyRing } from '../../types';
import SecretReveal from './SecretReveal';

import './ClientsPanel.scss';

const messages = defineMessages({
  loading: { id: 'Loading clients', defaultMessage: 'Loading clients…' },
  registered: {
    id: 'Registered clients',
    defaultMessage: 'Registered clients',
  },
  type: { id: 'Type', defaultMessage: 'Type' },
  publicClient: {
    id: 'Public (PKCE required)',
    defaultMessage: 'Public (PKCE required)',
  },
  confidential: { id: 'Confidential', defaultMessage: 'Confidential' },
  grants: { id: 'Grants', defaultMessage: 'Grants' },
  redirectUris: { id: 'Redirect URIs', defaultMessage: 'Redirect URIs' },
  scope: { id: 'Scope', defaultMessage: 'Scope' },
  enable: { id: 'Enable', defaultMessage: 'Enable' },
  disable: { id: 'Disable', defaultMessage: 'Disable' },
  rotateSecret: { id: 'Rotate secret', defaultMessage: 'Rotate secret' },
  unregister: { id: 'Unregister', defaultMessage: 'Unregister' },
  disabledNotice: {
    id: 'Disabled. Its existing access tokens are refused as well.',
    defaultMessage:
      'Disabled. Its existing access tokens are refused as well: the ' +
      'audience is checked against this registry on every request.',
  },
  noClients: {
    id: 'No clients are registered yet.',
    defaultMessage: 'No clients are registered yet.',
  },
  register: { id: 'Register a client', defaultMessage: 'Register a client' },
  clientId: { id: 'Client ID', defaultMessage: 'Client ID' },
  title: { id: 'Title', defaultMessage: 'Title' },
  redirectUrisHelp: {
    id: 'One per line. Matched exactly.',
    defaultMessage:
      'One per line. Matched exactly — a trailing slash or an extra query ' +
      'parameter is a different URI.',
  },
  scopeHelp: {
    id: 'Space separated, for example “openid profile email”.',
    defaultMessage: 'Space separated, for example “openid profile email”.',
  },
  publicClientLabel: { id: 'Public client', defaultMessage: 'Public client' },
  publicClientHelp: {
    id: 'A browser or native app, which cannot keep a secret.',
    defaultMessage:
      'A browser or native app, which cannot keep a secret. PKCE is ' +
      'required for these and no secret is issued.',
  },
  submit: { id: 'Register', defaultMessage: 'Register' },
  signingKeys: { id: 'Signing keys', defaultMessage: 'Signing keys' },
  ring: {
    id: '{total} of {size} in the ring, signing with {algorithm}.',
    defaultMessage:
      '{total} of {size} in the ring, signing with {algorithm}. Public keys ' +
      'are published at {jwks}.',
  },
  signing: { id: 'signing', defaultMessage: 'signing' },
  verifyingOnly: {
    id: 'verifying only',
    defaultMessage: 'verifying only',
  },
  rotateKey: {
    id: 'Rotate signing key',
    defaultMessage: 'Rotate signing key',
  },
  ringWarning: {
    id: 'Older keys stay in the ring so tokens already issued keep verifying.',
    defaultMessage:
      'Older keys stay in the ring so tokens already issued keep verifying. ' +
      'The ring holds {size}; rotating more than that within one ' +
      'access-token lifetime will invalidate tokens still in flight.',
  },
  loadingKeys: { id: 'Loading keys', defaultMessage: 'Loading keys…' },
});

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

/** What a `<dd>` shows when the client has nothing for that field. */
const NOTHING = '—';

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
  const intl = useIntl();
  const [draft, setDraft] = useState({ ...BLANK });

  if (loading) {
    return (
      <div className="identity-clients" role="status">
        {intl.formatMessage(messages.loading)}
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
        <h2>{intl.formatMessage(messages.registered)}</h2>
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
                  <dt>{intl.formatMessage(messages.type)}</dt>
                  <dd>
                    {intl.formatMessage(
                      client.public
                        ? messages.publicClient
                        : messages.confidential,
                    )}
                  </dd>
                  <dt>{intl.formatMessage(messages.grants)}</dt>
                  <dd>{client.grant_types.join(', ') || NOTHING}</dd>
                  <dt>{intl.formatMessage(messages.redirectUris)}</dt>
                  <dd>{client.redirect_uris.join(', ') || NOTHING}</dd>
                  <dt>{intl.formatMessage(messages.scope)}</dt>
                  <dd>{client.scope || NOTHING}</dd>
                </dl>
                <div className="identity-clients__actions">
                  <button
                    type="button"
                    className="identity-button"
                    disabled={busy}
                    onClick={() => onToggle(client.client_id, !client.enabled)}
                  >
                    {intl.formatMessage(
                      client.enabled ? messages.disable : messages.enable,
                    )}
                  </button>
                  {client.public ? null : (
                    <button
                      type="button"
                      className="identity-button"
                      disabled={busy}
                      onClick={() => onRotateSecret(client.client_id)}
                    >
                      {intl.formatMessage(messages.rotateSecret)}
                    </button>
                  )}
                  <button
                    type="button"
                    className="identity-button identity-button--danger"
                    data-action="delete"
                    disabled={busy}
                    onClick={() => onDelete(client.client_id)}
                  >
                    {intl.formatMessage(messages.unregister)}
                  </button>
                </div>
                {client.enabled ? null : (
                  <p
                    className="identity-clients__disabled identity-note"
                    role="status"
                  >
                    {intl.formatMessage(messages.disabledNotice)}
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="identity-clients__empty identity-note">
            {intl.formatMessage(messages.noClients)}
          </p>
        )}
      </section>

      <section className="identity-clients__new">
        <h2>{intl.formatMessage(messages.register)}</h2>
        <form onSubmit={submit}>
          <label>
            {intl.formatMessage(messages.clientId)}
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
            {intl.formatMessage(messages.title)}
            <input
              type="text"
              value={draft.title}
              onChange={(event) =>
                setDraft({ ...draft, title: event.target.value })
              }
            />
          </label>
          <label>
            {intl.formatMessage(messages.redirectUris)}
            <textarea
              rows={3}
              value={draft.redirect_uris}
              onChange={(event) =>
                setDraft({ ...draft, redirect_uris: event.target.value })
              }
            />
            <small>{intl.formatMessage(messages.redirectUrisHelp)}</small>
          </label>
          <label>
            {intl.formatMessage(messages.scope)}
            <input
              type="text"
              value={draft.scope}
              onChange={(event) =>
                setDraft({ ...draft, scope: event.target.value })
              }
            />
            <small>{intl.formatMessage(messages.scopeHelp)}</small>
          </label>
          <label>
            <input
              type="checkbox"
              checked={draft.public}
              onChange={(event) =>
                setDraft({ ...draft, public: event.target.checked })
              }
            />
            {intl.formatMessage(messages.publicClientLabel)}
            <small>{intl.formatMessage(messages.publicClientHelp)}</small>
          </label>
          <button type="submit" className="identity-button" disabled={busy}>
            {intl.formatMessage(messages.submit)}
          </button>
        </form>
      </section>

      <section className="identity-clients__keys">
        <h2>{intl.formatMessage(messages.signingKeys)}</h2>
        {keys ? (
          <>
            <p>
              <FormattedMessage
                {...messages.ring}
                values={{
                  total: keys.items_total,
                  size: keys.ring_size,
                  algorithm: keys.algorithm,
                  jwks: <a href={keys.jwks_uri}>{keys.jwks_uri}</a>,
                }}
              />
            </p>
            <ul>
              {keys.items.map((key) => (
                <li key={key.kid} data-kid={key.kid}>
                  <code>{key.kid}</code>
                  {key.active ? (
                    <strong> — {intl.formatMessage(messages.signing)}</strong>
                  ) : (
                    ` — ${intl.formatMessage(messages.verifyingOnly)}`
                  )}
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="identity-button"
              disabled={busy}
              onClick={onRotateKey}
            >
              {intl.formatMessage(messages.rotateKey)}
            </button>
            <p className="identity-clients__keys-warning identity-note">
              {intl.formatMessage(messages.ringWarning, {
                size: keys.ring_size,
              })}
            </p>
          </>
        ) : (
          <p role="status">{intl.formatMessage(messages.loadingKeys)}</p>
        )}
      </section>
    </div>
  );
};

export default ClientsPanel;
