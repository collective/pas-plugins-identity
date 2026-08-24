/**
 * The "email me a link" half of the login page.
 * @module components/Login/MagicLinkForm
 */
import React, { useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';

import './MagicLinkForm.scss';

const messages = defineMessages({
  email: { id: 'Email address', defaultMessage: 'Email address' },
  send: { id: 'Email me a link', defaultMessage: 'Email me a link' },
  sent: {
    id: 'If that address can sign in here',
    defaultMessage:
      'If that address can sign in here, a link is on its way. It works ' +
      'once, and only for a few minutes.',
  },
  failed: {
    id: 'That did not work. Please try again in a little while.',
    defaultMessage: 'That did not work. Please try again in a little while.',
  },
});

interface MagicLinkFormProps {
  sent: boolean;
  loading: boolean;
  error?: unknown;
  onSend: (email: string) => void;
}

const MagicLinkForm: React.FC<MagicLinkFormProps> = ({
  sent,
  loading,
  error,
  onSend,
}) => {
  const intl = useIntl();
  const [email, setEmail] = useState('');

  if (sent) {
    // Deliberately says nothing about whether the address is known: the
    // backend answers identically either way, and a UI that distinguished
    // them would undo that.
    return (
      <p
        className="identity-magic-link identity-magic-link--sent"
        role="status"
      >
        {intl.formatMessage(messages.sent)}
      </p>
    );
  }

  return (
    <form
      className="identity-magic-link"
      onSubmit={(event) => {
        event.preventDefault();
        if (email.trim()) {
          onSend(email.trim());
        }
      }}
    >
      <label htmlFor="identity-magic-link-email">
        {intl.formatMessage(messages.email)}
      </label>
      <input
        id="identity-magic-link-email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        disabled={loading}
        onChange={(event) => setEmail(event.target.value)}
      />
      <button
        type="submit"
        className="identity-button"
        disabled={loading || !email.trim()}
      >
        {intl.formatMessage(messages.send)}
      </button>
      {error ? (
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.failed)}
        </p>
      ) : null}
    </form>
  );
};

export default MagicLinkForm;
