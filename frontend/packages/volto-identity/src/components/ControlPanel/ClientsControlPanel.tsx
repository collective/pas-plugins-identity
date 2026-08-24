/**
 * Control-panel container: store, dispatch, and page chrome around the
 * clients panel.
 *
 * The chrome is the same chrome the providers panel has, which is Volto's
 * own: a centred container, a titled panel, and the toolbar with a route
 * back to the control-panel listing. Without it this route rendered as bare
 * markup with no way out of it at all.
 * @module components/ControlPanel/ClientsControlPanel
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { Container, Segment } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import backSVG from '@plone/volto/icons/back.svg';

import {
  createClient,
  deleteClient,
  listClients,
  listKeys,
  rotateClientSecret,
  rotateKey,
  updateClient,
} from '../../actions';
import ClientsPanel from './ClientsPanel';
import type { OAuthClient } from '../../types';

const messages = defineMessages({
  // The configlet's own title, so the page, the browser tab and the entry in
  // the control-panel listing all say the same thing.
  title: { id: 'OAuth clients', defaultMessage: 'OAuth clients' },
  back: { id: 'Back', defaultMessage: 'Back' },
});

const ClientsControlPanel: React.FC = () => {
  const intl = useIntl();
  const isClient = useClient();
  const { pathname } = useLocation();
  const dispatch = useDispatch();
  // Held here rather than read from the store on every render: the secret
  // must survive the re-listing that follows a create, and it must disappear
  // when the operator says they have saved it rather than when some other
  // request happens to resolve.
  const [minted, setMinted] = useState<OAuthClient | null>(null);

  const clients = useSelector((state: any) => state.oauthClients);
  const keys = useSelector((state: any) => state.signingKeys);
  const created = useSelector((state: any) => state.clientCreate);
  const rotated = useSelector((state: any) => state.clientSecretRotate);
  const updated = useSelector((state: any) => state.clientUpdate);
  const removed = useSelector((state: any) => state.clientDelete);
  const keyRotated = useSelector((state: any) => state.keyRotate);

  useEffect(() => {
    dispatch(listClients());
    dispatch(listKeys());
  }, [dispatch]);

  useEffect(() => {
    if (created?.loaded || updated?.loaded || removed?.loaded) {
      // Re-read rather than patch the local copy: the listing never carries
      // the secret, and a locally patched entry would.
      dispatch(listClients());
    }
  }, [dispatch, created?.loaded, updated?.loaded, removed?.loaded]);

  useEffect(() => {
    if (keyRotated?.loaded) {
      dispatch(listKeys());
    }
  }, [dispatch, keyRotated?.loaded]);

  useEffect(() => {
    const answer = created?.loaded ? created.data : null;
    if (answer?.secret) {
      setMinted(answer);
    }
  }, [created?.loaded, created?.data]);

  useEffect(() => {
    const answer = rotated?.loaded ? rotated.data : null;
    if (answer?.secret) {
      setMinted(answer);
    }
  }, [rotated?.loaded, rotated?.data]);

  const onCreate = useCallback(
    (data: Record<string, unknown>) => {
      dispatch(createClient(data));
    },
    [dispatch],
  );

  const onToggle = useCallback(
    (clientId: string, enabled: boolean) => {
      dispatch(updateClient(clientId, { enabled }));
    },
    [dispatch],
  );

  const onRotateSecret = useCallback(
    (clientId: string) => {
      dispatch(rotateClientSecret(clientId));
    },
    [dispatch],
  );

  const onDelete = useCallback(
    (clientId: string) => {
      dispatch(deleteClient(clientId));
    },
    [dispatch],
  );

  const onRotateKey = useCallback(() => {
    dispatch(rotateKey());
  }, [dispatch]);

  const onDismissSecret = useCallback(() => setMinted(null), []);

  return (
    <div id="page-controlpanel" className="identity-controlpanel">
      <Helmet title={intl.formatMessage(messages.title)} />
      <Container>
        <Segment.Group raised>
          <Segment className="primary">
            {intl.formatMessage(messages.title)}
          </Segment>
          <Segment>
            <ClientsPanel
              clients={clients?.data ?? []}
              keys={keys?.data ?? null}
              loading={Boolean(clients?.loading)}
              busy={Boolean(
                created?.loading ||
                  updated?.loading ||
                  removed?.loading ||
                  rotated?.loading ||
                  keyRotated?.loading,
              )}
              minted={minted}
              onCreate={onCreate}
              onToggle={onToggle}
              onRotateSecret={onRotateSecret}
              onDelete={onDelete}
              onRotateKey={onRotateKey}
              onDismissSecret={onDismissSecret}
            />
          </Segment>
        </Segment.Group>
      </Container>
      {isClient &&
        createPortal(
          <Toolbar
            pathname={pathname}
            hideDefaultViewButtons
            inner={
              <Link className="item" to="/controlpanel">
                <Icon
                  name={backSVG}
                  className="circled"
                  size="30px"
                  title={intl.formatMessage(messages.back)}
                />
              </Link>
            }
          />,
          document.getElementById('toolbar') as HTMLElement,
        )}
    </div>
  );
};

export default ClientsControlPanel;
