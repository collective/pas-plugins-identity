/**
 * The "email me a link" way in.
 *
 * The markup and the classes are `PasswordForm`'s, which are
 * `volto-authomatic`'s `PloneForm`, which is the shape Volto's own login form
 * has: a labelled field with a single underline, and the submit as an icon
 * button on a divided row. The two forms on this page ask for one and two
 * fields respectively and are otherwise the same form -- which is the point.
 * Before this they were not: a bare `<label>` and `<input>` next to a fully
 * dressed `PloneAuth`, on the same card, one click apart.
 *
 * Just the form. Whether it is shown at all, and what it replaces when it is,
 * belongs to `LoginForm`.
 * @module components/Login/MagicLinkForm
 */
import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { Button, Container, TextField } from '@plone/components';
import { defineMessages, useIntl } from 'react-intl';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import aheadSVG from '@plone/volto/icons/ahead.svg';

// The widget's own stylesheet, for the same reason `PasswordForm` imports it:
// `@plone/components` ships its CSS separately from its components, so a
// TextField rendered without this is unstyled.
import '@plone/components/src/styles/basic/TextField.css';

import LoginOverlay, { useDismissibleError } from './LoginOverlay';

import './MagicLinkForm.scss';

const messages = defineMessages({
  email: { id: 'Email address', defaultMessage: 'Email address' },
  send: { id: 'Email me a link', defaultMessage: 'Email me a link' },
  sending: { id: 'Sending', defaultMessage: 'Sending' },
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
  const [showError, dismissError] = useDismissibleError(error);

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

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (email.trim()) {
      onSend(email.trim());
    }
  };

  return (
    <form
      method="post"
      className="PloneAuth identity-magic-link"
      onSubmit={submit}
    >
      <Container className="form">
        <TextField
          label={intl.formatMessage(messages.email)}
          name="email"
          type="email"
          placeholder={intl.formatMessage(messages.email)}
          autoComplete="email"
          isRequired
          value={email}
          onChange={setEmail}
        />
      </Container>

      <Container className="actions">
        <Button
          id="magic-link-form-submit"
          type="submit"
          isDisabled={loading || !email.trim()}
          aria-label={intl.formatMessage(
            loading ? messages.sending : messages.send,
          )}
        >
          <Icon className="circled" name={aheadSVG} size="30px" />
        </Button>
      </Container>

      {loading ? (
        <LoginOverlay message={intl.formatMessage(messages.sending)} />
      ) : null}

      {showError ? (
        <LoginOverlay
          error
          message={intl.formatMessage(messages.failed)}
          onDismiss={dismissError}
        />
      ) : null}
    </form>
  );
};

export default MagicLinkForm;
