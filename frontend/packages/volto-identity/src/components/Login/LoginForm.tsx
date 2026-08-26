/**
 * The login page, without any store or routing in it.
 *
 * Kept presentational so it can be tested by rendering it, which is where
 * the behaviour worth pinning lives: which buttons appear, what is disabled
 * while a redirect is in flight, and what a failure says.
 * @module components/Login/LoginForm
 */
import React, { useEffect, useRef, useState } from 'react';
import { Container } from '@plone/components';
import { defineMessages, useIntl } from 'react-intl';

import type { LoginProvider } from '../../types';
import { EMAIL_DRIVER } from '../../helpers/identities';
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
  redirecting: {
    id: 'Taking you to {provider}…',
    defaultMessage: 'Taking you to {provider}…',
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
  /**
   * Whether Plone's own password form is one of the ways in.
   *
   * A prop rather than a read of `config.settings` here, so this component
   * stays renderable without the registry and the decision is visible in
   * one place.
   */
  showPloneLogin: boolean;
  onSelectProvider: (provider: LoginProvider) => void;
  onSendMagicLink: (email: string) => void;
  onPasswordLogin: (username: string, password: string) => void;
}

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
  showPloneLogin,
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
  // With nothing configured the password form is the login page whatever the
  // setting says. The setting decides whether a password is offered *beside*
  // the providers; it is not a way to leave a site with no way in, which is
  // what a fresh install -- add-on on, no provider configured yet -- would
  // otherwise be.
  const hasPassword = showPloneLogin || !providers.length;
  // Every way in, counted the same way whatever kind it is: this is what
  // decides whether there is a choice to present at all.
  const ways = buttons.length + (hasMagicLink ? 1 : 0) + (hasPassword ? 1 : 0);
  const onlyProvider = ways === 1 && buttons.length === 1 ? buttons[0] : null;

  // A single provider and nothing else: the picker would be one button asking
  // the user to confirm the only thing that can happen. Sent once per mount
  // and never while a failure is on screen -- an unreachable provider would
  // otherwise be an unbreakable redirect loop rather than a message with a
  // button under it.
  const startedRef = useRef(false);
  useEffect(() => {
    if (!onlyProvider || error || starting || startedRef.current) {
      return;
    }
    startedRef.current = true;
    onSelectProvider(onlyProvider);
  }, [onlyProvider, error, starting, onSelectProvider]);

  if (loading) {
    return (
      <div className="identity-login" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }

  if (ways === 1 && hasPassword) {
    // Not an error: a site can legitimately have no providers configured yet,
    // and an authorization server may never have any -- its users are local.
    // So the password form is the login page, shown outright rather than
    // behind a disclosure, and nothing announces the absence: the panel's
    // description already says the account is one on this site. This is what
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

  if (ways === 1 && hasMagicLink) {
    // The same argument as the password form above: one way in is not a
    // choice, so it is not presented as one.
    return (
      <div className="identity-login identity-login--empty">
        <MagicLinkForm
          sent={magicLinkSent}
          loading={magicLinkLoading}
          error={magicLinkError}
          onSend={onSendMagicLink}
        />
      </div>
    );
  }

  if (onlyProvider && !error) {
    // The redirect is already on its way from the effect above. Saying so
    // beats a flash of a button nobody is meant to press.
    return (
      <div className="identity-login" role="status">
        {intl.formatMessage(messages.redirecting, {
          provider: onlyProvider.title || onlyProvider.id,
        })}
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
          rather than a line of text under them -- when it is offered at all.
          A site that turned it off and has only the magic link renders an
          empty list here and the form below it. */}
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
        {hasPassword ? (
          <li>
            <ProviderButton
              driver={PASSWORD_DRIVER}
              label={intl.formatMessage(messages.usePassword)}
              disabled={starting}
              onSelect={() => setPassword(true)}
            />
          </li>
        ) : null}
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
