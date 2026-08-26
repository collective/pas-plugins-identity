/**
 * The "add an email address" half of the identities page.
 * @module components/Identities/EmailLinkForm
 */
import React, { useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';

import './EmailLinkForm.scss';

const messages = defineMessages({
  heading: {
    id: 'Add an email address',
    defaultMessage: 'Add an email address',
  },
  explain: {
    id: 'Adding an address lets you sign in with a link',
    defaultMessage:
      'We will email a link to confirm the address belongs to you. Once ' +
      'confirmed, you can sign in with it.',
  },
  email: { id: 'Email address', defaultMessage: 'Email address' },
  send: {
    id: 'Send confirmation link',
    defaultMessage: 'Send confirmation link',
  },
  sent: {
    id: 'Check that inbox for a confirmation link',
    defaultMessage:
      'Check that inbox. The link works once, and only for a few minutes, ' +
      'and it has to be opened while you are still signed in here.',
  },
});

interface EmailLinkFormProps {
  /** Whether the confirmation mail has gone out. */
  sent: boolean;
  loading: boolean;
  onSend: (email: string) => void;
}

// No `error` prop, deliberately: the panel around this form already renders
// one refusal for the whole page, and a second one here would report the
// same failure twice.

const EmailLinkForm: React.FC<EmailLinkFormProps> = ({
  sent,
  loading,
  onSend,
}) => {
  const intl = useIntl();
  const [email, setEmail] = useState('');

  if (sent) {
    // Unlike the login form's version, this one may name the address: the
    // person reading it is signed in and typed the address themselves, so
    // there is nothing here to enumerate.
    return (
      <div className="identity-email-link identity-email-link--sent">
        <h3>{intl.formatMessage(messages.heading)}</h3>
        <p role="status">{intl.formatMessage(messages.sent)}</p>
      </div>
    );
  }

  return (
    <form
      className="identity-email-link"
      onSubmit={(event) => {
        event.preventDefault();
        if (email.trim()) {
          onSend(email.trim());
        }
      }}
    >
      <h3>{intl.formatMessage(messages.heading)}</h3>
      <p className="identity-note">{intl.formatMessage(messages.explain)}</p>
      <label htmlFor="identity-email-link-address">
        {intl.formatMessage(messages.email)}
      </label>
      <input
        id="identity-email-link-address"
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
        data-action="link-email"
        disabled={loading || !email.trim()}
      >
        {intl.formatMessage(messages.send)}
      </button>
    </form>
  );
};

export default EmailLinkForm;
