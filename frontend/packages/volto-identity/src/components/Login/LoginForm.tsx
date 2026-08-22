/**
 * The login page, without any store or routing in it.
 *
 * Kept presentational so it can be tested by rendering it, which is where
 * the behaviour worth pinning lives: which buttons appear, what is disabled
 * while a redirect is in flight, and what a failure says.
 * @module components/Login/LoginForm
 */
import React from 'react';
import type { LoginProvider } from '../../types';
import MagicLinkForm from './MagicLinkForm';
import PasswordForm from './PasswordForm';
import ProviderButton from './ProviderButton';

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
  const buttons = providers.filter((p) => p.driver !== EMAIL_DRIVER);
  const hasMagicLink = providers.some((p) => p.driver === EMAIL_DRIVER);

  if (loading) {
    return (
      <div className="identity-login" role="status">
        Loading sign-in options…
      </div>
    );
  }

  if (!providers.length) {
    // Not an error: a site can legitimately have none configured yet, and
    // saying so beats an empty page that looks broken.
    // A site can legitimately have no providers configured yet, and an
    // authorization server may never have any: its users are local. Saying
    // "no sign-in options" while hiding the one that works was how this page
    // left an identity provider with no way in at all.
    return (
      <div className="identity-login identity-login--empty">
        <p>No sign-in providers are configured for this site.</p>
        <PasswordForm
          loading={passwordLoading}
          error={passwordError}
          onSubmit={onPasswordLogin}
        />
      </div>
    );
  }

  return (
    <div className="identity-login">
      {buttons.length ? (
        <ul className="identity-providers">
          {buttons.map((provider) => (
            <li key={provider.id}>
              <ProviderButton
                provider={provider}
                disabled={starting}
                onSelect={onSelectProvider}
              />
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p className="identity-error" role="alert">
          That sign-in option is not available right now.
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

      <PasswordForm
        loading={passwordLoading}
        error={passwordError}
        onSubmit={onPasswordLogin}
      />
    </div>
  );
};

export default LoginForm;
