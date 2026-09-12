/**
 * Everything the login card needs from the store and the router.
 *
 * The login page and the sign-in block show the same card: the same heading,
 * the same description strip, the same ways in. What they ask of the store,
 * and what the card says, is therefore written once. What each puts around
 * the card, and whether a sole provider is started without asking, stays with
 * each of them.
 * @module components/Login/useLogin
 */
import { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import {
  listLoginProviders,
  sendMagicLink,
  startProviderLogin,
} from '../../actions';
import { login } from '@plone/volto/actions/userSession/userSession';

import { goTo } from '../../helpers/navigate';
import { returnUrl } from '../../helpers/returnUrl';
import { showPloneLogin } from '../../helpers/showPloneLogin';
import type { LoginProvider } from '../../types';
import type { LoginFormProps } from './LoginForm';

const messages = defineMessages({
  title: { id: 'Log in', defaultMessage: 'Log in' },
  chooseHow: {
    id: 'Choose how you would like to sign in.',
    defaultMessage: 'Choose how you would like to sign in.',
  },
  signInLocally: {
    id: 'Sign in with your account on this site.',
    defaultMessage: 'Sign in with your account on this site.',
  },
});

/** What the login card is given, as `useLogin` answers it. */
export interface LoginState {
  /**
   * Every prop `LoginForm` takes but `redirectToSoleProvider`.
   *
   * That one is left to the caller: the page decides it from the visit, and
   * the block never redirects at all.
   */
  form: Omit<LoginFormProps, 'redirectToSoleProvider'>;
  /** The card's heading. */
  title: string;
  /**
   * The card's description strip, naming what is below it.
   *
   * `undefined` until the provider listing has answered.
   */
  description: string | undefined;
  /** The session token as it was on the first render, or `''`. */
  sessionOnArrival: string;
}

/**
 * List the ways in, and carry out whichever one is chosen.
 *
 * Once somebody signs in while this is mounted, it takes them back to where
 * the flow started: the whole request, for an authorization request.
 *
 * @returns The card's props and what the caller decides around them.
 */
export function useLogin(): LoginState {
  const intl = useIntl();
  const dispatch = useDispatch();
  const location = useLocation();
  const { push } = useHistory();
  const [redirecting, setRedirecting] = useState(false);

  const providers = useSelector((state: any) => state.loginProviders);
  const started = useSelector((state: any) => state.providerLogin);
  const magic = useSelector((state: any) => state.magicLinkSend);
  const userSession = useSelector((state: any) => state.userSession);

  // The session as it was when this mounted. Only a token that appears
  // *after* that is somebody signing in here.
  //
  // Taken by the initialiser, while rendering, rather than by an effect. The
  // form decides whether to redirect in an effect of its own, and a child's
  // effects run before those of the component rendering it: filled in by an
  // effect here, this would still be empty when that decision is made.
  const [sessionOnArrival] = useState<string>(() => userSession?.token ?? '');

  useEffect(() => {
    dispatch(listLoginProviders());
  }, [dispatch]);

  useEffect(() => {
    if (redirecting && started?.loaded && started?.data?.authorize_url) {
      // A full page load, not a router push: the next stop is the provider's
      // own origin.
      goTo(started.data.authorize_url, push, { external: true });
    }
  }, [redirecting, started, push]);

  const onSelectProvider = useCallback(
    (provider: LoginProvider) => {
      setRedirecting(true);
      dispatch(
        startProviderLogin(
          provider.id,
          returnUrl(location.search, location.pathname),
        ),
      );
    },
    [dispatch, location.search, location.pathname],
  );

  const onPasswordLogin = useCallback(
    (username: string, password: string) => {
      dispatch(login(username, password));
    },
    [dispatch],
  );

  const onSendMagicLink = useCallback(
    (email: string) => {
      dispatch(sendMagicLink(email));
    },
    [dispatch],
  );

  // Volto stores the token and its own AppExtras redirects; all this has to
  // do is get the user back to where the flow started, which for an
  // authorization request is the whole request.
  //
  // Only for a token that appeared while this was mounted. Arriving at the
  // login page *already* carrying one means whatever sent us there would not
  // accept it, because that page is only reached when something refused the
  // session -- so bouncing straight back is an infinite redirect, and the
  // sign-in options never stay on screen long enough to be clicked. Showing
  // the form instead lets the visitor sign in as somebody the flow will
  // accept.
  useEffect(() => {
    const token = userSession?.token;
    if (token && token !== sessionOnArrival) {
      goTo(returnUrl(location.search, location.pathname), push);
    }
  }, [
    userSession?.token,
    sessionOnArrival,
    location.search,
    location.pathname,
    push,
  ]);

  // Whether the listing has answered at all -- which is not the same thing as
  // `loading`. The slice starts neither loading nor loaded, so between the
  // first render and the effect above dispatching, `loading` is false and
  // `data` is empty: indistinguishable, to anything reading those two, from a
  // site with no providers configured. That is the state the page used to
  // render the local password form in, for a tick, before replacing it.
  //
  // A failed listing is deliberately *not* held here. It has answered -- with
  // nothing -- and the form's own fallbacks are what a site with no reachable
  // provider list should get: the password form is the way in when this page
  // cannot draw the other ones.
  const answered = Boolean(providers?.loaded || providers?.error);

  // The description names what is actually below, which differs by site: a
  // provider list, a password form, or both. Until the listing answers there
  // is nothing below to name, so the strip is left out rather than guessing
  // -- guessing means the wrong sentence on screen and then a second one
  // replacing it.
  const description = answered
    ? intl.formatMessage(
        providers?.data?.length ? messages.chooseHow : messages.signInLocally,
      )
    : undefined;

  return {
    form: {
      providers: providers?.data ?? [],
      loading: !answered,
      starting: redirecting,
      error: started?.error,
      magicLinkSent: Boolean(magic?.data),
      magicLinkLoading: Boolean(magic?.loading),
      magicLinkError: magic?.error,
      passwordLoading: Boolean(userSession?.login?.loading),
      passwordError: userSession?.login?.error,
      showPloneLogin: showPloneLogin(),
      onSelectProvider,
      onSendMagicLink,
      onPasswordLogin,
    },
    title: intl.formatMessage(messages.title),
    description,
    sessionOnArrival,
  };
}
