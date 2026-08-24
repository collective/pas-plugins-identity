/**
 * Identities container: the linking UI in user settings.
 * @module components/Identities/Identities
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Container, Segment } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import { getBaseUrl } from '@plone/volto/helpers/Url/Url';
import backSVG from '@plone/volto/icons/back.svg';

import { listIdentities, startLinking, unlinkIdentity } from '../../actions';
import { linkable } from '../../helpers/identities';
import type { Identity, LoginProvider } from '../../types';
import IdentitiesList from './IdentitiesList';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
  back: { id: 'Back', defaultMessage: 'Back' },
});

const Identities: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const location = useLocation();
  const { pathname } = location;
  const [redirecting, setRedirecting] = useState(false);

  const mine = useSelector((state: any) => state.identities);
  const offered = useSelector((state: any) => state.loginProviders);
  const linking = useSelector((state: any) => state.identityLinking);
  const removing = useSelector((state: any) => state.identityUnlink);

  useEffect(() => {
    // One request: the providers ride along as an expanded component.
    dispatch(listIdentities(true));
  }, [dispatch]);

  useEffect(() => {
    if (redirecting && linking?.loaded && linking?.data?.authorize_url) {
      window.location.href = linking.data.authorize_url;
    }
  }, [redirecting, linking]);

  useEffect(() => {
    if (removing?.loaded) {
      // The list is stale the moment an unlink succeeds, and can_unlink may
      // have changed for everything left.
      dispatch(listIdentities());
    }
  }, [dispatch, removing?.loaded]);

  const onLink = useCallback(
    (provider: LoginProvider) => {
      setRedirecting(true);
      dispatch(startLinking(provider.id, location.pathname));
    },
    [dispatch, location.pathname],
  );

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
            available={linkable(offered?.data ?? [], mine?.data ?? [])}
            loading={Boolean(mine?.loading)}
            busy={redirecting || Boolean(removing?.loading)}
            error={linking?.error ?? removing?.error}
            onLink={onLink}
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
