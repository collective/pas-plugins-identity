/**
 * Identities container: the linking UI in user settings.
 * @module components/Identities/Identities
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useHistory, useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Container, Segment } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import { getBaseUrl } from '@plone/volto/helpers/Url/Url';
import backSVG from '@plone/volto/icons/back.svg';

import {
  getMyProfile,
  listIdentities,
  setPreferredEmail,
  startLinking,
  unlinkIdentity,
} from '../../actions';
import { EMAIL_DRIVER } from '../../helpers/identities';
import type { Identity, LoginProvider, ProfileEmail } from '../../types';
import IdentitiesList from './IdentitiesList';
import { goTo } from '../../helpers/navigate';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
  back: { id: 'Back', defaultMessage: 'Back' },
});

const Identities: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const location = useLocation();
  const { push } = useHistory();
  const { pathname } = location;
  const [redirecting, setRedirecting] = useState(false);

  const mine = useSelector((state: any) => state.identities);
  const linkableProviders = useSelector(
    (state: any) => state.linkableProviders,
  );
  // The login page's own listing, which arrives expanded on `@identities`.
  // Hidden providers are absent from it -- that is what `show_in_login` means
  // -- so it is the only thing that can say whether a method here is one
  // anybody can actually sign in with.
  const loginProviders = useSelector((state: any) => state.loginProviders);
  const linking = useSelector((state: any) => state.identityLinking);
  const removing = useSelector((state: any) => state.identityUnlink);
  const preferring = useSelector((state: any) => state.preferredEmail);
  // The addresses live on the profile, not on the identity records, so this
  // page needs the one endpoint that reads them off the catalog brain.
  const myProfile = useSelector((state: any) => state.myProfile);

  useEffect(() => {
    // Expanded, so the login page's own listing rides along: this page has to
    // know which of these methods actually signs anybody in, and that is the
    // question `@login-providers` answers. One request rather than two, which
    // is what the expandable component exists for.
    dispatch(listIdentities(true));
    dispatch(getMyProfile());
  }, [dispatch]);

  useEffect(() => {
    if (redirecting && linking?.loaded && linking?.data?.authorize_url) {
      goTo(linking.data.authorize_url, push, { external: true });
    }
  }, [redirecting, linking, push]);

  // The email provider answers `sent` instead of an authorize URL, and the
  // page stays where it is to say so.
  const emailSent = Boolean(linking?.loaded && linking?.data?.sent);

  // An operator who takes the email provider off the login page has turned
  // off signing in with a link. Verifying an address still does its other
  // job -- recognising the same person behind a later provider login -- so
  // what changes here is what this page claims, not what it offers.
  const canSignInWithLink = (loginProviders?.data ?? []).some(
    (provider: LoginProvider) => provider.driver === EMAIL_DRIVER,
  );

  useEffect(() => {
    if (removing?.loaded) {
      // The list is stale the moment an unlink succeeds, and can_unlink may
      // have changed for everything left. So are the addresses: removing an
      // email identity is exactly what un-verifies one.
      dispatch(listIdentities(true));
      dispatch(getMyProfile());
    }
  }, [dispatch, removing?.loaded]);

  const onLink = useCallback(
    (provider: LoginProvider) => {
      setRedirecting(true);
      dispatch(startLinking(provider.id, location.pathname));
    },
    [dispatch, location.pathname],
  );

  const onVerifyEmail = useCallback(
    (address: string) => {
      // No `setRedirecting` here: nothing is going to navigate. The flow
      // continues when the link in the message is clicked, which may well be
      // in another browser entirely.
      //
      // The provider id is the driver id, which is what this site's email
      // provider is called by convention and what the backend's own
      // `EMAIL_PROVIDER` is. A site that renamed it would need the id off the
      // listing instead -- but the listing deliberately does not carry the
      // email provider any more, which is the whole point of this panel.
      dispatch(startLinking(EMAIL_DRIVER, location.pathname, address));
    },
    [dispatch, location.pathname],
  );

  const onPreferEmail = useCallback(
    (address: string) => {
      // The whole list, reordered here rather than on the backend: `emails`
      // is a field, and a PATCH carrying one entry would replace the list
      // with it. The rest keep their order, so this moves one address and
      // rearranges nothing else.
      const profileUrl = myProfile?.data?.profile;
      if (!profileUrl) {
        return;
      }
      const addresses: string[] = (myProfile?.data?.emails ?? []).map(
        (entry: ProfileEmail) => entry.address,
      );
      dispatch(
        setPreferredEmail(flattenToAppURL(profileUrl), [
          address,
          ...addresses.filter((each) => each !== address),
        ]),
      );
    },
    [dispatch, myProfile],
  );

  useEffect(() => {
    if (preferring?.loaded) {
      // A PATCH answers with no body, so the new order comes from asking
      // again -- and `preferred` is derived, so the answer is the only place
      // that knows which address actually won.
      dispatch(getMyProfile());
    }
  }, [dispatch, preferring?.loaded]);

  const onUnlink = useCallback(
    (identity: Identity) => {
      dispatch(unlinkIdentity(identity.provider, identity.subject));
    },
    [dispatch],
  );

  return (
    // The page chrome Volto's own user-settings pages have: a container that
    // centres the content, a titled panel, and the toolbar. Without it this
    // route rendered as a bare list against the left edge of the window.
    <Container id="page-identities">
      <Helmet title={intl.formatMessage(messages.title)} />
      <Segment.Group raised>
        <Segment className="primary">
          {intl.formatMessage(messages.title)}
        </Segment>
        <Segment>
          <IdentitiesList
            identities={mine?.data ?? []}
            available={linkableProviders?.data ?? []}
            emails={myProfile?.data?.emails ?? []}
            canSignInWithLink={canSignInWithLink}
            profileUrl={myProfile?.data?.profile ?? null}
            loading={Boolean(mine?.loading)}
            busy={
              redirecting ||
              Boolean(removing?.loading) ||
              Boolean(preferring?.loading) ||
              Boolean(linking?.loading)
            }
            error={linking?.error ?? removing?.error}
            emailSent={emailSent}
            onLink={onLink}
            onVerifyEmail={onVerifyEmail}
            onPreferEmail={onPreferEmail}
            onUnlink={onUnlink}
          />
        </Segment>
      </Segment.Group>
      {isClient &&
        createPortal(
          <Toolbar
            pathname={pathname}
            hideDefaultViewButtons
            inner={
              <Link to={`${getBaseUrl(pathname)}`} className="item">
                <Icon
                  name={backSVG}
                  className="contents circled"
                  size="30px"
                  title={intl.formatMessage(messages.back)}
                />
              </Link>
            }
          />,
          document.getElementById('toolbar') as HTMLElement,
        )}
    </Container>
  );
};

export default Identities;
