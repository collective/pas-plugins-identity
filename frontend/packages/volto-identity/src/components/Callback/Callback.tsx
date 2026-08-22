/**
 * The route the provider redirects back to.
 *
 * This is the frontend half of the Volto-route callback shape: the provider
 * sends the browser here with `code` and `state` on the query string, or the
 * emailed magic link arrives with `magic_link`. Either way the credential is
 * handed to the backend, which is the only thing that can validate it.
 * @module components/Callback/Callback
 */
import React, { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';
import { LOGIN } from '@plone/volto/constants/ActionTypes';

import { completeCallback, confirmMagicLink } from '../../actions';
import { readCallback } from '../../helpers/callback';

interface CallbackProps {
  /** Called with the issued token instead of the default sign-in. */
  onToken?: (token: string, cameFrom: string) => void;
}

const Callback: React.FC<CallbackProps> = ({ onToken }) => {
  const dispatch = useDispatch();
  const location = useLocation();
  const dispatched = useRef(false);
  const [refusal, setRefusal] = useState<string | null>(null);

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
        parsed.kind === 'error'
          ? 'The provider refused the sign-in.'
          : 'This sign-in link is incomplete.',
      );
    }
  }, [dispatch, location.search]);

  const answered = callback?.loaded ? callback : magic?.loaded ? magic : null;

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

  if (refusal) {
    return (
      <div className="identity-callback identity-callback--error" role="alert">
        {refusal}
      </div>
    );
  }

  if (callback?.error || magic?.error) {
    // Every backend refusal reads the same on purpose: expired, replayed,
    // forged and wrong-session are one message here, and the audit log
    // carries the difference.
    return (
      <div className="identity-callback identity-callback--error" role="alert">
        That sign-in link is no longer valid. Please start again.
      </div>
    );
  }

  return (
    <div className="identity-callback" role="status">
      Signing you in…
    </div>
  );
};

export default Callback;
