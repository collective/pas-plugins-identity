/**
 * Signing in with a local account.
 *
 * This route replaces Volto's own login page, so without it a site that
 * installs this add-on loses password sign-in entirely. That is wrong for any
 * site with local accounts and impossible for one running the `[server]`
 * layer: an authorization server has to be able to authenticate its own
 * users, and "sign in with somebody else" is not an answer it can give.
 *
 * The markup and the classes follow `volto-authomatic`'s `PloneForm`, which
 * is the shape Volto's own login form has: labelled fields with a single
 * underline, and a submit and a cancel as icon buttons on a divided row.
 *
 * Kept behind a disclosure and last on the page. The providers are the point
 * of this add-on; the password is the fallback.
 * @module components/Login/PasswordForm
 */
import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { Button, Container, TextField } from '@plone/components';
import { Link } from 'react-router-dom';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import aheadSVG from '@plone/volto/icons/ahead.svg';
import clearSVG from '@plone/volto/icons/clear.svg';

// The widget's own stylesheet. `@plone/components` ships its CSS separately
// from its components, so a TextField rendered without this is unstyled --
// which is what made this form look unlike volto-authomatic's despite the
// markup and the class names matching it exactly.
import '@plone/components/src/styles/basic/TextField.css';

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

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (username && password) {
      onSubmit(username, password);
    }
  };

  const clear = () => {
    setUsername('');
    setPassword('');
  };

  if (!open) {
    return (
      <Container className="identity-password-toggle">
        <button type="button" onClick={() => setOpen(true)}>
          Sign in with a password
        </button>
      </Container>
    );
  }

  return (
    <form method="post" className="PloneAuth" onSubmit={submit}>
      <Container className="form">
        <TextField
          label="Login name"
          name="username"
          placeholder="Login name"
          autoComplete="username"
          isRequired
          value={username}
          onChange={setUsername}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          placeholder="Password"
          autoComplete="current-password"
          isRequired
          value={password}
          onChange={setPassword}
        />
      </Container>

      <Container className="forgotPassword">
        <p className="help">
          <Link to="/passwordreset">Forgot your password?</Link>
        </p>
      </Container>

      {error ? (
        // One message for a wrong name and a wrong password alike: telling
        // them apart is an account-enumeration oracle.
        <Container className="identity-error" role="alert">
          That login name and password did not match.
        </Container>
      ) : null}

      <Container className="actions">
        <Button
          id="login-form-submit"
          type="submit"
          isDisabled={loading || !username || !password}
          aria-label={loading ? 'Signing in' : 'Sign in'}
        >
          <Icon className="circled" name={aheadSVG} size="30px" />
        </Button>

        <Button
          id="login-form-cancel"
          type="button"
          onPress={clear}
          aria-label="Clear"
        >
          <Icon className="circled" name={clearSVG} size="30px" />
        </Button>
      </Container>
    </form>
  );
};

export default PasswordForm;
