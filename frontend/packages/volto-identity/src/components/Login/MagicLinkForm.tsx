/**
 * The "email me a link" half of the login page.
 * @module components/Login/MagicLinkForm
 */
import React, { useState } from 'react';

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
        If that address can sign in here, a link is on its way. It works once,
        and only for a few minutes.
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
      <label htmlFor="identity-magic-link-email">Email address</label>
      <input
        id="identity-magic-link-email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        disabled={loading}
        onChange={(event) => setEmail(event.target.value)}
      />
      <button type="submit" disabled={loading || !email.trim()}>
        Email me a link
      </button>
      {error ? (
        <p className="identity-error" role="alert">
          That did not work. Please try again in a little while.
        </p>
      ) : null}
    </form>
  );
};

export default MagicLinkForm;
