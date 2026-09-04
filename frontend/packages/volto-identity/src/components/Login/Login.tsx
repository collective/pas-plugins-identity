/**
 * Login container: store, routing, and the redirect out to the provider.
 * @module components/Login/Login
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import {
  listLoginProviders,
  sendMagicLink,
  startProviderLogin,
} from '../../actions';
import { login } from '@plone/volto/actions/userSession/userSession';

import { returnUrl } from '../../helpers/returnUrl';
import { showPloneLogin } from '../../helpers/showPloneLogin';
import type { LoginProvider } from '../../types';
import LoginForm from './LoginForm';
import LoginPanel from './LoginPanel';
import { goTo } from '../../helpers/navigate';

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

const Login: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const location = useLocation();
  const { push } = useHistory();
  const [redirecting, setRedirecting] = useState(false);
  // The session as it was when this page loaded. Only a token that appears
  // *after* that is somebody signing in here.
  const sessionOnArrival = useRef<string | undefined>(undefined);

  const providers = useSelector((state: any) => state.loginProviders);
  const started = useSelector((state: any) => state.providerLogin);
  const magic = useSelector((state: any) => state.magicLinkSend);
  const userSession = useSelector((state: any) => state.userSession);

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

  useEffect(() => {
    if (sessionOnArrival.current === undefined) {
      sessionOnArrival.current = userSession?.token ?? '';
    }
  }, [userSession?.token]);

  // Volto stores the token and its own AppExtras redirects; all this has to
  // do is get the user back to where the flow started, which for an
  // authorization request is the whole request.
  //
  // Only for a token that appeared while this page was open. Arriving here
  // *already* carrying one means whatever sent us here would not accept it,
  // because this page is only reached when something refused the session --
  // so bouncing straight back is an infinite redirect, and the sign-in
  // options never stay on screen long enough to be clicked. Showing the form
  // instead lets the visitor sign in as somebody the flow will accept.
  useEffect(() => {
    const token = userSession?.token;
    const arrived = sessionOnArrival.current;
    if (token && arrived !== undefined && token !== arrived) {
      goTo(returnUrl(location.search, location.pathname), push);
    }
  }, [userSession?.token, location.search, location.pathname, push]);

  const onSendMagicLink = useCallback(
    (email: string) => {
      dispatch(sendMagicLink(email));
    },
    [dispatch],
  );

  // Whether the listing has answered at all -- which is not the same thing as
  // `loading`. The slice starts neither loading nor loaded, so between the
  // first render and the effect below dispatching, `loading` is false and
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
  const hasProviders = Boolean(providers?.data?.length);
  const description = answered
    ? intl.formatMessage(
        hasProviders ? messages.chooseHow : messages.signInLocally,
      )
    : undefined;

  return (
    <LoginPanel
      title={intl.formatMessage(messages.title)}
      description={description}
    >
      <LoginForm
        providers={providers?.data ?? []}
        loading={!answered}
        starting={redirecting}
        error={started?.error}
        magicLinkSent={Boolean(magic?.data)}
        magicLinkLoading={Boolean(magic?.loading)}
        magicLinkError={magic?.error}
        onSelectProvider={onSelectProvider}
        onSendMagicLink={onSendMagicLink}
        passwordLoading={Boolean(userSession?.login?.loading)}
        passwordError={userSession?.login?.error}
        showPloneLogin={showPloneLogin()}
        onPasswordLogin={onPasswordLogin}
      />
    </LoginPanel>
  );
};

export default Login;
