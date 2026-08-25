/**
 * Applications container: the authorized-applications page in user settings.
 *
 * Chrome and store, the way the identities page has them; the panel below
 * does the rendering. This one adds the confirmation, because withdrawing is
 * the destructive half and the person doing it should know what it costs
 * before it happens rather than read about it afterwards.
 * @module components/Applications/Applications
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Container, Segment } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';
import { toast } from 'react-toastify';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import Toast from '@plone/volto/components/manage/Toast/Toast';
import { getBaseUrl } from '@plone/volto/helpers/Url/Url';
import backSVG from '@plone/volto/icons/back.svg';

import { listGrants, withdrawGrant } from '../../actions';
import ApplicationsPanel from './ApplicationsPanel';

const messages = defineMessages({
  title: { id: 'Applications', defaultMessage: 'Applications' },
  back: { id: 'Back', defaultMessage: 'Back' },
  confirm: {
    id: 'Withdraw access for {client}?',
    defaultMessage:
      'Withdraw access for {client}? It will be signed out everywhere and ' +
      'will have to ask you again next time.',
  },
  withdrawn: {
    id: 'Access withdrawn',
    defaultMessage: 'Access withdrawn',
  },
  error: { id: 'Error', defaultMessage: 'Error' },
});

const Applications: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const { pathname } = useLocation();
  // Which client is being withdrawn, so only that row's button goes dead
  // rather than the whole list.
  const [withdrawing, setWithdrawing] = useState<string | null>(null);
  // Which one's details are on screen. Held here rather than in the URL: a
  // detail view is a way of reading one row of this page, not a page of its
  // own, and a bookmark to somebody's authorization of one application is
  // not a thing worth being able to share.
  const [selected, setSelected] = useState<string | null>(null);

  const grants = useSelector((state: any) => state.oauthGrants);

  useEffect(() => {
    dispatch(listGrants());
  }, [dispatch]);

  const onWithdraw = useCallback(
    (clientId: string) => {
      const grant = grants?.data?.items?.find(
        (item: { client_id: string }) => item.client_id === clientId,
      );
      // eslint-disable-next-line no-alert
      const agreed = window.confirm(
        intl.formatMessage(messages.confirm, {
          client: grant?.title || clientId,
        }),
      );
      if (!agreed) {
        return;
      }
      setWithdrawing(clientId);
      (dispatch(withdrawGrant(clientId)) as any)
        .then(() => {
          toast.success(
            <Toast success title={intl.formatMessage(messages.withdrawn)} />,
          );
          // Back to the list: the application whose details were on screen
          // is the one that just stopped existing.
          setSelected(null);
          // Re-read rather than drop the row locally: the listing is what
          // says whether anything is left, and a locally pruned one would
          // disagree with the server the moment anything else changed.
          dispatch(listGrants());
        })
        .catch((err: any) => {
          toast.error(
            <Toast
              error
              title={intl.formatMessage(messages.error)}
              content={err?.response?.body?.error?.message ?? String(err)}
            />,
          );
        })
        .finally(() => setWithdrawing(null));
    },
    [dispatch, grants?.data?.items, intl],
  );

  return (
    <Container id="page-applications">
      <Helmet title={intl.formatMessage(messages.title)} />
      <Segment.Group raised>
        <Segment className="primary">
          {intl.formatMessage(messages.title)}
        </Segment>
        <Segment>
          <ApplicationsPanel
            grants={grants?.data ?? null}
            loading={Boolean(grants?.loading)}
            error={grants?.error}
            selected={selected}
            withdrawing={withdrawing}
            onSelect={setSelected}
            onWithdraw={onWithdraw}
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

export default Applications;
