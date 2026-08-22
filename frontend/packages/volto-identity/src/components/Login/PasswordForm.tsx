/**
 * Signing in with a local account.
 *
 * This route replaces Volto's own login page, so without it a site that
 * installs this add-on loses password sign-in entirely. That is wrong for any
 * site with local accounts and impossible for one running the `[server]`
 * layer: an authorization server has to be able to authenticate its own
 * users, and "sign in with somebody else" is not an answer it can give.
 *
 * Kept last on the page and behind a disclosure. The providers are the point
 * of this add-on; the password is the fallback.
 * @module components/Login/PasswordForm
 */
import React, { useState } from 'react';

interface PasswordFormProps {
  /** Whether a sign-in attempt is in flight. */
  loading: boolean;
  /** Whether the last attempt was refused. */
  error?: unknown;
  /** Called with the credentials to try. */
  onSubmit: (username: string, password: string) => void;
}

const PasswordForm: React.FC<PasswordFormProps> = ({
  loading,
  error,
  onSubmit,
}) => {
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (username && password) {
      onSubmit(username, password);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        className="identity-password-toggle"
        onClick={() => setOpen(true)}
      >
        Sign in with a password
      </button>
    );
  }

  return (
    <form className="identity-password" onSubmit={submit}>
      <label htmlFor="identity-username">Login name</label>
      <input
        id="identity-username"
        name="username"
        type="text"
        autoComplete="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />

      <label htmlFor="identity-password">Password</label>
      <input
        id="identity-password"
        name="password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      {error ? (
        // One message for a wrong name and a wrong password alike: telling
        // them apart is an account-enumeration oracle.
        <p className="identity-error" role="alert">
          That login name and password did not match.
        </p>
      ) : null}

      <button type="submit" disabled={loading || !username || !password}>
        {loading ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  );
};

export default PasswordForm;
