/**
 * The route that asks whether to hand the session token to a local
 * application, and does it.
 *
 * Every way in ends here when a handoff is pending: a provider's callback, a
 * magic link, the password form, and a visitor who arrived already signed
 * in. See `helpers/handoff` for the contract.
 *
 * The request and the token are taken once, when the page first has both,
 * and the page renders from that copy. Allow clears the pending request
 * while the browser is posting the form; a page that re-read it would stop
 * rendering the form, and the browser would cancel a submission whose form
 * is gone (collective/volto-authomatic#52). For the same reason nothing here
 * navigates after Allow.
 * @module components/Handoff/Handoff
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { useHistory } from 'react-router-dom';

import {
  clearHandoff,
  pendingHandoff,
  type HandoffRequest,
} from '../../helpers/handoff';
import { nameFromToken } from '../../helpers/token';
import HandoffPanel from './HandoffPanel';

interface Snapshot {
  request: HandoffRequest;
  token: string;
}

/**
 * The login page URL that starts a handoff again.
 *
 * @param request The pending request.
 * @returns A site-relative URL.
 */
export function restartUrl(request: HandoffRequest): string {
  const params = new URLSearchParams({
    return_url: request.returnUrl,
    state: request.state,
  });
  return `/login?${params.toString()}`;
}

const Handoff: React.FC = () => {
  const { push, replace } = useHistory();
  const token: string = useSelector(
    (state: any) => state.userSession?.token ?? '',
  );
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const allowed = useRef(false);

  // In an effect, so the server renders nothing: the request is a cookie
  // this page reads in the browser, and the site's address is the browser's.
  useEffect(() => {
    if (snapshot || allowed.current) {
      return;
    }
    const request = pendingHandoff();
    if (!request) {
      clearHandoff();
      replace('/');
      return;
    }
    if (!token) {
      // Signed out on the way here: sign in again, and come back.
      replace(restartUrl(request));
      return;
    }
    setSnapshot({ request, token });
  }, [snapshot, token, replace]);

  const onAllow = useCallback(() => {
    allowed.current = true;
    clearHandoff();
  }, []);

  const onDeny = useCallback(() => {
    clearHandoff();
    push('/');
  }, [push]);

  if (!snapshot) {
    return null;
  }

  return (
    <HandoffPanel
      request={snapshot.request}
      token={snapshot.token}
      user={nameFromToken(snapshot.token)}
      site={typeof window === 'undefined' ? '' : window.location.host}
      onAllow={onAllow}
      onDeny={onDeny}
    />
  );
};

export default Handoff;
