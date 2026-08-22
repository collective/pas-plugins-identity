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
import type { OAuthClient } from '../../types';

interface SecretRevealProps {
  client: OAuthClient;
  onDismiss: () => void;
}

const SecretReveal: React.FC<SecretRevealProps> = ({ client, onDismiss }) => {
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
        Secret for <code>{client.client_id}</code>
      </h3>

      <p className="identity-secret__notice">
        {client.notice ??
          'This is the only time this secret is shown. It is stored hashed ' +
            'and cannot be read back; if it is lost, rotate it.'}
      </p>

      <div className="identity-secret__value">
        {/* Read-only rather than plain text so it can be selected and copied
            with the keyboard by somebody not using a mouse. */}
        <input
          type="text"
          readOnly
          value={client.secret ?? ''}
          aria-label={`Client secret for ${client.client_id}`}
          onFocus={(event) => event.currentTarget.select()}
        />
        <button type="button" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      <button
        type="button"
        className="identity-secret__dismiss"
        onClick={onDismiss}
      >
        I have saved it
      </button>
    </section>
  );
};

export default SecretReveal;
