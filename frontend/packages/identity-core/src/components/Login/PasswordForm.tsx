/**
 * Signing in with a local account.
 *
 * The add-on's login route replaces the frontend's own login page, so without
 * this form a site that installs it loses password sign-in entirely. That is wrong for any
 * site with local accounts and impossible for one running the `[server]`
 * layer: an authorization server has to be able to authenticate its own
 * users, and "sign in with somebody else" is not an answer it can give.
 *
 * The markup and the classes follow `volto-authomatic`'s `PloneForm`, which
 * is the shape Volto's own login form has: labelled fields with a single
 * underline, and a submit and a cancel as icon buttons on a divided row.
 *
 * Just the form. Whether it is shown at all, and what it replaces when it is,
 * belongs to `LoginForm`: opening the password form hides the providers, and a
 * component cannot hide its own siblings.
 * @module components/Login/PasswordForm
 */
import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { Button, Container, TextField } from '@plone/components';
import { defineMessages } from '#i18n';

// The widget's own stylesheet. `@plone/components` ships its CSS separately
// from its components, so a TextField rendered without this is unstyled --
// which is what made this form look unlike volto-authomatic's despite the
// markup and the class names matching it exactly.
import '@plone/components/src/styles/basic/TextField.css';

import { useIdentityUI } from '../IdentityUI/IdentityUI';
import LoginOverlay, { useDismissibleError } from './LoginOverlay';

import './PasswordForm.scss';

const messages = defineMessages({
  loginName: { id: 'Login name', defaultMessage: 'Login name' },
  password: { id: 'Password', defaultMessage: 'Password' },
  forgotPassword: {
    id: 'box_forgot_password_option',
    defaultMessage: 'Forgot your password?',
  },
  refused: {
    id: 'That login name and password did not match.',
    defaultMessage: 'That login name and password did not match.',
  },
  signIn: { id: 'Sign in', defaultMessage: 'Sign in' },
  signingIn: { id: 'Signing in', defaultMessage: 'Signing in' },
  clear: { id: 'Clear', defaultMessage: 'Clear' },
});

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
  const { t, Link, icons } = useIdentityUI();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showError, dismissError] = useDismissibleError(error);

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

  return (
    <form method="post" className="PloneAuth" onSubmit={submit}>
      <Container className="form">
        <TextField
          label={t(messages.loginName)}
          name="username"
          placeholder={t(messages.loginName)}
          autoComplete="username"
          isRequired
          value={username}
          onChange={setUsername}
        />
        <TextField
          label={t(messages.password)}
          name="password"
          type="password"
          placeholder={t(messages.password)}
          autoComplete="current-password"
          isRequired
          value={password}
          onChange={setPassword}
        />
      </Container>

      <Container className="forgotPassword">
        <p className="help">
          <Link href="/passwordreset">{t(messages.forgotPassword)}</Link>
        </p>
      </Container>

      <Container className="actions">
        <Button
          id="login-form-submit"
          type="submit"
          isDisabled={loading || !username || !password}
          aria-label={t(loading ? messages.signingIn : messages.signIn)}
        >
          {icons.submit}
        </Button>

        <Button
          id="login-form-cancel"
          type="button"
          onPress={clear}
          aria-label={t(messages.clear)}
        >
          {icons.clear}
        </Button>
      </Container>

      {/* Over the form rather than inside it: a refusal that pushed the
          action row down moved the button the reader was about to press
          again. The wait carries no dismiss -- it is not theirs to end. */}
      {loading ? <LoginOverlay message={t(messages.signingIn)} /> : null}

      {/* One message for a wrong name and a wrong password alike: telling
          them apart is an account-enumeration oracle. */}
      {showError ? (
        <LoginOverlay
          error
          message={t(messages.refused)}
          onDismiss={dismissError}
        />
      ) : null}
    </form>
  );
};

export default PasswordForm;
