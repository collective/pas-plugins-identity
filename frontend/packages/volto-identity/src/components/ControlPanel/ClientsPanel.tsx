/**
 * The OAuth client control panel, without store or routing.
 *
 * Shaped after the providers panel, which is itself shaped after Volto's
 * own: a table of what exists, the add and save actions in the toolbar
 * rather than inline, and the form rendered by Volto's `Form` from a schema.
 * Nothing here lays out an input.
 *
 * Which view is on screen is the container's decision, because the toolbar
 * buttons that switch between them live there. This renders the one it is
 * given: the client list, a client's form, the signing keys, or the server's
 * own settings.
 * @module components/ControlPanel/ClientsPanel
 */
import React from 'react';
import { FormattedMessage, defineMessages, useIntl } from 'react-intl';
import { Button, Segment, Table } from 'semantic-ui-react';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import { Form } from '@plone/volto/components/manage/Form';
import deleteSVG from '@plone/volto/icons/delete.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';
import refreshSVG from '@plone/volto/icons/refresh.svg';

import { clientSchema, toFormData } from '../../helpers/clientSchema';
import type {
  JsonSchema,
  OAuthClient,
  ServerSettingsPanel,
  SigningKeyRing,
} from '../../types';
import SecretReveal from './SecretReveal';

import './ClientsPanel.scss';
import ConfirmModal from './ConfirmModal';

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
  scope: { id: 'Scope', defaultMessage: 'Scope' },
  edit: { id: 'Edit', defaultMessage: 'Edit' },
  rotateSecret: { id: 'Rotate secret', defaultMessage: 'Rotate secret' },
  unregister: { id: 'Unregister', defaultMessage: 'Unregister' },
  confirmDelete: {
    id: 'Unregister this client?',
    defaultMessage:
      'Unregister this client? Every token already minted for it stops ' +
      'being accepted at once.',
  },
  noClients: {
    id: 'No clients are registered yet.',
    defaultMessage: 'No clients are registered yet.',
  },
  add: { id: 'Register a client', defaultMessage: 'Register a client' },
  columnTitle: { id: 'Title', defaultMessage: 'Title' },
  columnId: { id: 'Client ID', defaultMessage: 'Client ID' },
  columnEnabled: { id: 'Enabled', defaultMessage: 'Enabled' },
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  yes: { id: 'Yes', defaultMessage: 'Yes' },
  no: { id: 'No', defaultMessage: 'No' },
  disabledNotice: {
    id: 'Disabled. Its existing access tokens are refused as well.',
    defaultMessage:
      'Disabled. Its existing access tokens are refused as well: the ' +
      'audience is checked against this registry on every request.',
  },
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
  serverSettings: { id: 'Server settings', defaultMessage: 'Server settings' },
  loadingSettings: {
    id: 'Loading settings',
    defaultMessage: 'Loading settings…',
  },
  settingsUnavailable: {
    id: 'The server settings could not be read',
    defaultMessage:
      'The server settings could not be read, so they cannot be edited here.',
  },
  noIssuer: {
    id: 'No issuer is configured',
    defaultMessage:
      'No issuer is configured, so this server signs nothing and its ' +
      'discovery document answers 503. Set it under Server settings.',
  },
});

/** Which of the panel's views is on screen. */
export type ClientsView = 'list' | 'add' | 'edit' | 'keys' | 'settings';

interface ClientsPanelProps {
  clients: OAuthClient[];
  /**
   * The form's schema, as the backend serialized it from `IClientRecords`.
   *
   * Optional so a page talking to a backend that predates it, or one whose
   * request failed, renders an empty form rather than crashing on
   * `schema.fieldsets`.
   */
  schema?: JsonSchema;
  keys: SigningKeyRing | null;
  /**
   * The server's own settings, or null until they have arrived. The settings
   * form is built from the schema served with them, and the list warns while
   * they name no issuer.
   */
  settings?: ServerSettingsPanel | null;
  /** Whether reading the settings failed, as opposed to not having finished. */
  settingsFailed?: boolean;
  loading: boolean;
  busy: boolean;
  /** The client whose secret was just minted, if any. */
  minted: OAuthClient | null;
  view: ClientsView;
  /** The client being edited, when the view is `edit`. */
  editing: string | null;
  /** Handed to `Form`, so the toolbar's Save can submit it. */
  formRef: React.RefObject<any>;
  /** A failed request, rendered by `Form` above the fields. */
  error?: unknown;
  onSubmit: (data: Record<string, unknown>) => void;
  onSaveSettings: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  onEdit: (clientId: string) => void;
  onRotateSecret: (clientId: string) => void;
  onDelete: (clientId: string) => void;
  onRotateKey: () => void;
  onDismissSecret: () => void;
}

/** What a cell shows when the client has nothing for that column. */
const NOTHING = '—';

const ClientsPanel: React.FC<ClientsPanelProps> = ({
  clients,
  schema,
  keys,
  settings = null,
  settingsFailed = false,
  loading,
  busy,
  minted,
  view,
  editing,
  formRef,
  error,
  onSubmit,
  onSaveSettings,
  onCancel,
  onEdit,
  onRotateSecret,
  onDelete,
  onRotateKey,
  onDismissSecret,
}) => {
  const intl = useIntl();
  const current = editing
    ? clients.find((client) => client.client_id === editing)
    : undefined;
  const adding = view === 'add';

  const [confirming, setConfirming] = React.useState<string | null>(null);

  const confirmDelete = (clientId: string) => {
    setConfirming(clientId);
  };

  const onConfirmDelete = () => {
    const clientId = confirming;
    setConfirming(null);
    if (!clientId) {
      return;
    }
    onDelete(clientId);
  };

  const modal = (
    <ConfirmModal
      open={confirming !== null}
      header={confirming ?? ''}
      content={intl.formatMessage(messages.confirmDelete)}
      onCancel={() => setConfirming(null)}
      onConfirm={onConfirmDelete}
    />
  );

  if (view === 'keys') {
    return (
      <Segment.Group raised className="identity-clients">
        {modal}
        <Segment className="primary">
          {intl.formatMessage(messages.signingKeys)}
        </Segment>
        <Segment className="identity-clients__keys">
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
        </Segment>
      </Segment.Group>
    );
  }

  if (view === 'settings') {
    // Volto's `Form` reads `schema.fieldsets` on its first render, so it waits
    // for the schema rather than mounting empty and staying that way.
    if (!settings?.schema) {
      return (
        <Segment.Group raised className="identity-clients">
          <Segment className="primary">
            {intl.formatMessage(messages.serverSettings)}
          </Segment>
          <Segment>
            {settingsFailed ? (
              <p role="alert" className="identity-error">
                {intl.formatMessage(messages.settingsUnavailable)}
              </p>
            ) : (
              <p role="status">
                {intl.formatMessage(messages.loadingSettings)}
              </p>
            )}
          </Segment>
        </Segment.Group>
      );
    }
    return (
      <Form
        ref={formRef}
        key="settings"
        title={intl.formatMessage(messages.serverSettings)}
        // Served by the backend from the settings interface, so nothing here
        // describes a field, and the issuer rule it enforces is the same one
        // a PATCH from anywhere else meets.
        schema={settings.schema}
        formData={settings.data}
        requestError={error}
        onSubmit={onSaveSettings}
        onCancel={onCancel}
        hideActions
      />
    );
  }

  if (view === 'add' || view === 'edit') {
    return (
      <Form
        ref={formRef}
        // An add form and an edit form ask for different fields, and `Form`
        // seeds an add form's defaults in its constructor -- once, from the
        // schema it mounted with. Keyed so switching between them remounts
        // rather than carrying the previous form's state into the next.
        key={adding ? 'add' : editing ?? 'edit'}
        title={
          adding
            ? intl.formatMessage(messages.add)
            : current?.title || current?.client_id
        }
        schema={clientSchema(schema, adding, intl)}
        formData={toFormData(adding ? undefined : current)}
        requestError={error}
        onSubmit={onSubmit}
        onCancel={onCancel}
        hideActions
      />
    );
  }

  return (
    <Segment.Group raised className="identity-clients">
      {modal}
      <Segment className="primary">
        {intl.formatMessage(messages.registered)}
      </Segment>
      {settings && !settings.data?.server_issuer ? (
        // The first thing an operator meets after deploying, and until now
        // the only sign of it was a 503 from the discovery document.
        <Segment className="identity-clients__warning" secondary role="alert">
          <strong>{intl.formatMessage(messages.noIssuer)}</strong>
        </Segment>
      ) : null}
      <Segment>
        {minted ? (
          <SecretReveal client={minted} onDismiss={onDismissSecret} />
        ) : null}
        {loading ? (
          <p role="status">{intl.formatMessage(messages.loading)}</p>
        ) : clients.length ? (
          <Table selectable compact>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.columnTitle)}
                </Table.HeaderCell>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.columnId)}
                </Table.HeaderCell>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.type)}
                </Table.HeaderCell>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.grants)}
                </Table.HeaderCell>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.scope)}
                </Table.HeaderCell>
                <Table.HeaderCell>
                  {intl.formatMessage(messages.columnEnabled)}
                </Table.HeaderCell>
                <Table.HeaderCell textAlign="right">
                  {intl.formatMessage(messages.columnActions)}
                </Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {clients.map((client) => (
                <Table.Row key={client['@id']} data-client={client.client_id}>
                  <Table.Cell>
                    {client.title || client.client_id}
                    {client.enabled ? null : (
                      <p
                        className="identity-clients__disabled identity-note"
                        role="status"
                      >
                        {intl.formatMessage(messages.disabledNotice)}
                      </p>
                    )}
                  </Table.Cell>
                  <Table.Cell>
                    <code>{client.client_id}</code>
                  </Table.Cell>
                  <Table.Cell>
                    {intl.formatMessage(
                      client.public
                        ? messages.publicClient
                        : messages.confidential,
                    )}
                  </Table.Cell>
                  <Table.Cell>
                    {client.grant_types.join(', ') || NOTHING}
                  </Table.Cell>
                  <Table.Cell>{client.scope.join(', ') || NOTHING}</Table.Cell>
                  <Table.Cell>
                    {intl.formatMessage(
                      client.enabled ? messages.yes : messages.no,
                    )}
                  </Table.Cell>
                  <Table.Cell textAlign="right">
                    <Button
                      basic
                      icon
                      disabled={busy}
                      aria-label={intl.formatMessage(messages.edit)}
                      title={intl.formatMessage(messages.edit)}
                      onClick={() => onEdit(client.client_id)}
                    >
                      <Icon name={pencilSVG} size="20px" />
                    </Button>
                    {/* A public client has no secret to rotate: PKCE is
                        what stands in for one. */}
                    {client.public ? null : (
                      <Button
                        basic
                        icon
                        disabled={busy}
                        aria-label={intl.formatMessage(messages.rotateSecret)}
                        title={intl.formatMessage(messages.rotateSecret)}
                        onClick={() => onRotateSecret(client.client_id)}
                      >
                        <Icon name={refreshSVG} size="20px" />
                      </Button>
                    )}
                    <Button
                      basic
                      icon
                      data-action="delete"
                      disabled={busy}
                      aria-label={intl.formatMessage(messages.unregister)}
                      title={intl.formatMessage(messages.unregister)}
                      onClick={() => confirmDelete(client.client_id)}
                    >
                      <Icon name={deleteSVG} size="20px" />
                    </Button>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        ) : (
          <p className="identity-clients__empty identity-note">
            {intl.formatMessage(messages.noClients)}
          </p>
        )}
      </Segment>
    </Segment.Group>
  );
};

export default ClientsPanel;
