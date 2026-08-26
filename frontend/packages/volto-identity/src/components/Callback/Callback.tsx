/**
 * The route the provider redirects back to.
 *
 * This is the frontend half of the Volto-route callback shape: the provider
 * sends the browser here with `code` and `state` on the query string, or the
 * emailed magic link arrives with `magic_link`. Either way the credential is
 * handed to the backend, which is the only thing that can validate it.
 *
 * It renders inside `LoginPanel`, the same card the login page is, because it
 * is the same flow one redirect later -- this is what `volto-authomatic` does
 * with its own callback. A bare `<div>` here put its one line against the left
 * edge of the window, which reads as a broken page rather than a step.
 * @module components/Callback/Callback
 */
import React, { useEffect, useRef, useState } from 'react';
import type { MessageDescriptor } from 'react-intl';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';
import { LOGIN } from '@plone/volto/constants/ActionTypes';

import { completeCallback, confirmMagicLink } from '../../actions';
import { readCallback } from '../../helpers/callback';
import { IDENTITIES_PATH } from '../../config/routes';
import LoginPanel from '../Login/LoginPanel';

import './Callback.scss';

const messages = defineMessages({
  // The same id the login page's heading uses: the same card, so the same
  // word, and one translation covers both.
  title: { id: 'Log in', defaultMessage: 'Log in' },
  working: { id: 'Signing you in', defaultMessage: 'Signing you in…' },
  linking: {
    id: 'Confirming your address',
    defaultMessage: 'Confirming your address…',
  },
  refused: {
    id: 'The provider refused the sign-in.',
    defaultMessage: 'The provider refused the sign-in.',
  },
  incomplete: {
    id: 'This sign-in link is incomplete.',
    defaultMessage: 'This sign-in link is incomplete.',
  },
  invalid: {
    id: 'That sign-in link is no longer valid. Please start again.',
    defaultMessage: 'That sign-in link is no longer valid. Please start again.',
  },
});

interface CallbackProps {
  /** Called with the issued token instead of the default sign-in. */
  onToken?: (token: string, cameFrom: string) => void;
}

const Callback: React.FC<CallbackProps> = ({ onToken }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const location = useLocation();
  const dispatched = useRef(false);
  // The descriptor rather than the formatted string: what is stored is
  // which refusal happened, and rendering it is the renderer's job.
  const [refusal, setRefusal] = useState<MessageDescriptor | null>(null);

  const callback = useSelector((state: any) => state.identityCallback);
  const magic = useSelector((state: any) => state.magicLinkConfirm);

  useEffect(() => {
    if (dispatched.current) {
      return;
    }
    dispatched.current = true;

    const parsed = readCallback(location.search);
    if (parsed.kind === 'magic-link') {
      dispatch(confirmMagicLink(parsed.token as string));
    } else if (parsed.kind === 'code') {
      dispatch(
        completeCallback(
          parsed.provider as string,
          parsed.code as string,
          parsed.state as string,
        ),
      );
    } else {
      setRefusal(
        parsed.kind === 'error' ? messages.refused : messages.incomplete,
      );
    }
  }, [dispatch, location.search]);

  const answered = callback?.loaded ? callback : magic?.loaded ? magic : null;

  // A confirmation link carries the same `magic_link` parameter as a login
  // link -- the difference is in the token, so it is the answer that reveals
  // which one arrived.
  const linked = Boolean(answered?.data?.linked);

  useEffect(() => {
    if (!linked) {
      return;
    }
    // Back to where the flow was started from. A full load rather than a
    // router push: the identities list was fetched before this address
    // existed, and the page has to be told about it.
    window.location.href = IDENTITIES_PATH;
  }, [linked]);

  useEffect(() => {
    const token = answered?.data?.token;
    if (!token) {
      return;
    }
    const cameFrom = answered?.data?.came_from ?? '';
    if (onToken) {
      onToken(token, cameFrom);
      return;
    }

    // The default, and the reason this is not an optional prop with no
    // fallback: the route is registered as a bare component, so nothing
    // passes onToken, and a page that fetched a token and then did nothing
    // with it sat on "Signing you in…" forever with a 200 in the access log.
    //
    // Volto's own LOGIN_SUCCESS is the whole sign-in: `persistAuthToken`
    // subscribes to the store at client start and writes any new
    // `userSession.token` out to the cookie, so putting the token in the
    // store is what makes the browser signed in. Reproducing that by writing
    // the cookie here would be a second implementation of it.
    dispatch({ type: `${LOGIN}_SUCCESS`, result: { token } });
    // A full load rather than a router push: everything rendered so far was
    // rendered for an anonymous user.
    window.location.href = cameFrom || '/';
  }, [answered, onToken, dispatch]);

  // Every backend refusal reads the same on purpose: expired, replayed,
  // forged and wrong-session are one message here, and the audit log carries
  // the difference. A refusal parsed off the query string is the one thing
  // this page can say more precisely, because no credential ever reached the
  // backend for it to be vague about.
  const failure =
    refusal ?? (callback?.error || magic?.error ? messages.invalid : null);

  return (
    <LoginPanel title={intl.formatMessage(messages.title)}>
      {failure ? (
        <p className="identity-callback identity-callback--error" role="alert">
          {intl.formatMessage(failure)}
        </p>
      ) : (
        <p className="identity-callback" role="status">
          {intl.formatMessage(linked ? messages.linking : messages.working)}
        </p>
      )}
    </LoginPanel>
  );
};

export default Callback;
