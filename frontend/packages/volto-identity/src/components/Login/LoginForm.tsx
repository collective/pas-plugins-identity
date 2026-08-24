/**
 * The login page, without any store or routing in it.
 *
 * Kept presentational so it can be tested by rendering it, which is where
 * the behaviour worth pinning lives: which buttons appear, what is disabled
 * while a redirect is in flight, and what a failure says.
 * @module components/Login/LoginForm
 */
import React, { useState } from 'react';
import { Container } from '@plone/components';
import { defineMessages, useIntl } from 'react-intl';

import type { LoginProvider } from '../../types';
import MagicLinkForm from './MagicLinkForm';
import PasswordForm from './PasswordForm';
import ProviderButton from './ProviderButton';

import './LoginForm.scss';

const messages = defineMessages({
  loading: {
    id: 'Loading sign-in options',
    defaultMessage: 'Loading sign-in options…',
  },
  unavailable: {
    id: 'That sign-in option is not available right now.',
    defaultMessage: 'That sign-in option is not available right now.',
  },
  usePassword: {
    id: 'Sign in with a password',
    defaultMessage: 'Sign in with a password',
  },
  backToOptions: {
    id: 'Back to sign-in options',
    defaultMessage: 'Back to sign-in options',
  },
});

interface LoginFormProps {
  providers: LoginProvider[];
  loading: boolean;
  starting: boolean;
  error?: unknown;
  magicLinkSent: boolean;
  magicLinkLoading: boolean;
  magicLinkError?: unknown;
  /** Whether a password sign-in is in flight. */
  passwordLoading: boolean;
  /** Whether the last password sign-in was refused. */
  passwordError?: unknown;
  onSelectProvider: (provider: LoginProvider) => void;
  onSendMagicLink: (email: string) => void;
  onPasswordLogin: (username: string, password: string) => void;
}

/** Providers handled by the magic-link form rather than a button. */
const EMAIL_DRIVER = 'email';

/**
 * The driver the local password button wears the colours of.
 *
 * `volto-authomatic` calls its own `plone`, and this reuses that name so the
 * two add-ons paint the same button the same blue.
 */
const PASSWORD_DRIVER = 'plone';

const LoginForm: React.FC<LoginFormProps> = ({
  providers,
  loading,
  starting,
  error,
  magicLinkSent,
  magicLinkLoading,
  magicLinkError,
  passwordLoading,
  passwordError,
  onSelectProvider,
  onSendMagicLink,
  onPasswordLogin,
}) => {
  const intl = useIntl();
  // The password form replaces the other ways in rather than sitting under
  // them: it is a different way to sign in, not an extra field on this one.
  // Held here because opening it hides its siblings, which the form itself
  // cannot do.
  const [password, setPassword] = useState(false);
  const buttons = providers.filter((p) => p.driver !== EMAIL_DRIVER);
  const hasMagicLink = providers.some((p) => p.driver === EMAIL_DRIVER);

  if (loading) {
    return (
      <div className="identity-login" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }

  if (!providers.length) {
    // Not an error: a site can legitimately have none configured yet, and an
    // authorization server may never have any -- its users are local. So the
    // password form is the login page, shown outright rather than behind a
    // disclosure, and nothing announces the absence: the panel's description
    // already says the account is one on this site. This is what
    // `volto-authomatic` renders when it has no providers either.
    return (
      <div className="identity-login identity-login--empty">
        <PasswordForm
          loading={passwordLoading}
          error={passwordError}
          onSubmit={onPasswordLogin}
        />
      </div>
    );
  }

  if (password) {
    return (
      <div className="identity-login">
        <PasswordForm
          loading={passwordLoading}
          error={passwordError}
          onSubmit={onPasswordLogin}
        />
        {/* Hiding the providers without a way back would strand anyone who
            opened this by mistake on the one form they cannot use. */}
        <Container className="identity-password-toggle">
          <button type="button" onClick={() => setPassword(false)}>
            {intl.formatMessage(messages.backToOptions)}
          </button>
        </Container>
      </div>
    );
  }

  return (
    <div className="identity-login">
      {/* The password is one of the ways in, so it is one of these buttons
          rather than a line of text under them. The list is therefore never
          empty here, even on a site whose only provider is the magic link. */}
      <ul className="identity-providers">
        {buttons.map((provider) => (
          <li key={provider.id}>
            <ProviderButton
              id={provider.id}
              driver={provider.driver}
              label={provider.title || provider.id}
              disabled={starting}
              onSelect={() => onSelectProvider(provider)}
            />
          </li>
        ))}
        <li>
          <ProviderButton
            driver={PASSWORD_DRIVER}
            label={intl.formatMessage(messages.usePassword)}
            disabled={starting}
            onSelect={() => setPassword(true)}
          />
        </li>
      </ul>

      {error ? (
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.unavailable)}
        </p>
      ) : null}

      {hasMagicLink ? (
        <MagicLinkForm
          sent={magicLinkSent}
          loading={magicLinkLoading}
          error={magicLinkError}
          onSend={onSendMagicLink}
        />
      ) : null}
    </div>
  );
};

export default LoginForm;
