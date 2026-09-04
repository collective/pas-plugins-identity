/**
 * What the login card says over itself: a wait, or a refusal.
 *
 * An overlay rather than a branch, because both used to *replace* what they
 * were about. A wait swapped the options for a line of text, so the card
 * changed size and the reader lost their place; a refusal appeared as a
 * paragraph that pushed everything below it down. Neither is a different
 * page -- they are something happening to the page that is already there, and
 * that is what an overlay is for.
 *
 * Two kinds, and the difference is who ends them. A wait ends when whatever
 * is being waited for answers, so it has no control on it. A refusal ends
 * when the reader has read it, so it does: leaving it up would hide the form
 * they need to try again in.
 *
 * Positioned against the nearest positioned ancestor, which is
 * `LoginPanel`'s `.form` -- the card's body, and the thing whose size should
 * not change while this is up.
 * @module components/Login/LoginOverlay
 */
import React, { useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';

import './LoginOverlay.scss';

const messages = defineMessages({
  dismiss: { id: 'Close', defaultMessage: 'Close' },
});

interface LoginOverlayProps {
  /** What is being waited for, or what was refused. */
  message: string;
  /**
   * Whether this is a refusal rather than a wait.
   *
   * A refusal is announced as an alert and carries no spinner: nothing is
   * happening, which is the whole message.
   */
  error?: boolean;
  /**
   * Take this overlay down.
   *
   * Only meaningful on a refusal -- a wait is not the reader's to end, and a
   * dismiss button on one would suggest it is. Absent even on a refusal where
   * there is nothing underneath to go back to.
   */
  onDismiss?: () => void;
}

const LoginOverlay: React.FC<LoginOverlayProps> = ({
  message,
  error = false,
  onDismiss,
}) => {
  const intl = useIntl();
  const kind = error ? 'identity-overlay--error' : 'identity-overlay--waiting';

  return (
    <div
      className={`identity-overlay ${kind}`}
      role={error ? 'alert' : 'status'}
    >
      <div className="identity-overlay__body">
        {error ? null : (
          <span className="identity-spinner" aria-hidden="true" />
        )}
        <p className="identity-overlay__message">{message}</p>
        {error && onDismiss ? (
          <button
            type="button"
            // Filled: it is the only thing on the overlay that can be
            // pressed, and an outlined button on a veil read as disabled.
            className="identity-button identity-button--primary"
            data-action="dismiss"
            onClick={onDismiss}
          >
            {intl.formatMessage(messages.dismiss)}
          </button>
        ) : null}
      </div>
    </div>
  );
};

/**
 * Whether a refusal is still worth showing, and how to stop showing it.
 *
 * The refusal itself lives in the store, so "dismissed" cannot: clearing it
 * there would be this component deciding a request never failed. What is
 * remembered instead is *which* refusal was dismissed, so the next one --
 * a second wrong password, a second unreachable provider -- says so again
 * rather than being silently swallowed by the first one's dismissal.
 *
 * The identity of the error value is what distinguishes them, which is what
 * the request reducers produce: a fresh object per failure. A backend that
 * somehow returned the very same object twice would have its second refusal
 * hidden, which is a better failure than a refusal that cannot be dismissed.
 *
 * @param error The refusal, or a falsy value when there is none.
 * @returns Whether to show it, and a function that takes it down.
 */
export function useDismissibleError(error: unknown): [boolean, () => void] {
  const [dismissed, setDismissed] = useState<unknown>(undefined);
  return [Boolean(error) && dismissed !== error, () => setDismissed(error)];
}

export default LoginOverlay;
