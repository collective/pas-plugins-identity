/**
 * The one moment a client secret exists.
 *
 * The server stores a scrypt hash and cannot read the secret back, so this is
 * shown once — at registration or rotation — and never again. That makes it
 * the one place in this add-on where dismissing a panel loses something
 * irrecoverable, so it says so plainly and does not close itself.
 * @module components/ControlPanel/SecretReveal
 */
import React, { useState } from 'react';
import { FormattedMessage, defineMessages, useIntl } from 'react-intl';

import type { OAuthClient } from '../../types';

import './SecretReveal.scss';

const messages = defineMessages({
  heading: {
    id: 'Secret for {clientId}',
    defaultMessage: 'Secret for {clientId}',
  },
  notice: {
    id: 'This is the only time this secret is shown.',
    defaultMessage:
      'This is the only time this secret is shown. It is stored hashed and ' +
      'cannot be read back; if it is lost, rotate it.',
  },
  secretFor: {
    id: 'Client secret for {clientId}',
    defaultMessage: 'Client secret for {clientId}',
  },
  copy: { id: 'Copy', defaultMessage: 'Copy' },
  copied: { id: 'Copied', defaultMessage: 'Copied' },
  dismiss: { id: 'I have saved it', defaultMessage: 'I have saved it' },
});

interface SecretRevealProps {
  client: OAuthClient;
  onDismiss: () => void;
}

const SecretReveal: React.FC<SecretRevealProps> = ({ client, onDismiss }) => {
  const intl = useIntl();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(client.secret ?? '');
      setCopied(true);
    } catch {
      // A browser that refuses clipboard access is not an error worth
      // reporting: the secret is on screen and selectable, which is the
      // fallback anyway.
      setCopied(false);
    }
  };

  return (
    <section
      className="identity-secret"
      role="alertdialog"
      aria-labelledby="identity-secret-heading"
    >
      <h3 id="identity-secret-heading">
        <FormattedMessage
          {...messages.heading}
          values={{ clientId: <code>{client.client_id}</code> }}
        />
      </h3>

      {/* The server's own notice when it sent one: it knows what it did --
          minted or rotated -- and this does not. */}
      <p className="identity-secret__notice">
        {client.notice ?? intl.formatMessage(messages.notice)}
      </p>

      <div className="identity-secret__value">
        {/* Read-only rather than plain text so it can be selected and copied
            with the keyboard by somebody not using a mouse. */}
        <input
          type="text"
          readOnly
          value={client.secret ?? ''}
          aria-label={intl.formatMessage(messages.secretFor, {
            clientId: client.client_id,
          })}
          onFocus={(event) => event.currentTarget.select()}
        />
        <button type="button" className="identity-button" onClick={copy}>
          {intl.formatMessage(copied ? messages.copied : messages.copy)}
        </button>
      </div>

      <button
        type="button"
        className="identity-button identity-secret__dismiss"
        onClick={onDismiss}
      >
        {intl.formatMessage(messages.dismiss)}
      </button>
    </section>
  );
};

export default SecretReveal;
