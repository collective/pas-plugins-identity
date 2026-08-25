/**
 * Control-panel container: store, dispatch, and page chrome around the
 * clients panel.
 *
 * The chrome is the providers panel's chrome, which is Volto's own: a
 * centred container, and a toolbar carrying the actions that switch what the
 * page shows -- the signing keys, a registration form, and the way back to
 * the control-panel listing. Which view is on is decided here rather than in
 * the panel, because those buttons live here.
 * @module components/ControlPanel/ClientsControlPanel
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { Button, Container } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';
import { toast } from 'react-toastify';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import Toast from '@plone/volto/components/manage/Toast/Toast';
import addSVG from '@plone/volto/icons/add.svg';
import backSVG from '@plone/volto/icons/back.svg';
import clearSVG from '@plone/volto/icons/clear.svg';
import keySVG from '@plone/volto/icons/key.svg';
import saveSVG from '@plone/volto/icons/save.svg';

import {
  createClient,
  deleteClient,
  listClients,
  listKeys,
  rotateClientSecret,
  rotateKey,
  updateClient,
} from '../../actions';
import { fromFormData } from '../../helpers/clientSchema';
import ClientsPanel from './ClientsPanel';
import type { ClientsView } from './ClientsPanel';
import type { OAuthClient } from '../../types';

const messages = defineMessages({
  // The configlet's own title, so the page, the browser tab and the entry in
  // the control-panel listing all say the same thing.
  title: { id: 'OAuth clients', defaultMessage: 'OAuth clients' },
  back: { id: 'Back', defaultMessage: 'Back' },
  add: { id: 'Register a client', defaultMessage: 'Register a client' },
  keys: { id: 'Signing keys', defaultMessage: 'Signing keys' },
  save: { id: 'Save', defaultMessage: 'Save' },
  cancel: { id: 'Cancel', defaultMessage: 'Cancel' },
  saved: { id: 'Changes saved', defaultMessage: 'Changes saved' },
  deleted: { id: 'Client unregistered', defaultMessage: 'Client unregistered' },
  rotated: { id: 'Signing key rotated', defaultMessage: 'Signing key rotated' },
  error: { id: 'Error', defaultMessage: 'Error' },
});

const ClientsControlPanel: React.FC = () => {
  const intl = useIntl();
  const isClient = useClient();
  const { pathname } = useLocation();
  const dispatch = useDispatch();
  const formRef = useRef<any>(null);

  const [view, setView] = useState<ClientsView>('list');
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
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

  const fail = useCallback(
    (err: any) => {
      setError(err);
      toast.error(
        <Toast
          error
          title={intl.formatMessage(messages.error)}
          content={err?.response?.body?.error?.message ?? String(err)}
        />,
      );
    },
    [intl],
  );

  const closeForm = useCallback(() => {
    setView('list');
    setEditing(null);
    setError(null);
  }, []);

  const succeed = useCallback(
    (message: string) => {
      toast.success(<Toast success title={message} />);
      closeForm();
      // Re-read rather than patch the local copy: the listing never carries
      // the secret, and a locally patched entry would.
      dispatch(listClients());
    },
    [closeForm, dispatch],
  );

  const onSubmit = useCallback(
    (data: Record<string, unknown>) => {
      const adding = view === 'add';
      const payload = fromFormData(data, adding);
      const action = adding
        ? createClient(payload)
        : updateClient(editing as string, payload);
      (dispatch(action) as any)
        .then(() => succeed(intl.formatMessage(messages.saved)))
        .catch(fail);
    },
    [dispatch, editing, fail, intl, succeed, view],
  );

  const onEdit = useCallback((clientId: string) => {
    setEditing(clientId);
    setError(null);
    setView('edit');
  }, []);

  const onRotateSecret = useCallback(
    (clientId: string) => {
      // No toast: the secret itself is what appears, and a success message
      // over it would be one more thing between the operator and the only
      // copy they will ever see.
      (dispatch(rotateClientSecret(clientId)) as any).catch(fail);
    },
    [dispatch, fail],
  );

  const onDelete = useCallback(
    (clientId: string) => {
      (dispatch(deleteClient(clientId)) as any)
        .then(() => succeed(intl.formatMessage(messages.deleted)))
        .catch(fail);
    },
    [dispatch, fail, intl, succeed],
  );

  const onRotateKey = useCallback(() => {
    (dispatch(rotateKey()) as any)
      .then(() => {
        toast.success(
          <Toast success title={intl.formatMessage(messages.rotated)} />,
        );
        dispatch(listKeys());
      })
      .catch(fail);
  }, [dispatch, fail, intl]);

  const onDismissSecret = useCallback(() => setMinted(null), []);

  const isForm = view === 'add' || view === 'edit';

  return (
    <div id="page-controlpanel" className="identity-controlpanel">
      <Helmet title={intl.formatMessage(messages.title)} />
      <Container>
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
          view={view}
          editing={editing}
          formRef={formRef}
          error={error}
          onSubmit={onSubmit}
          onCancel={closeForm}
          onEdit={onEdit}
          onRotateSecret={onRotateSecret}
          onDelete={onDelete}
          onRotateKey={onRotateKey}
          onDismissSecret={onDismissSecret}
        />
      </Container>
      {isClient &&
        createPortal(
          <Toolbar
            pathname={pathname}
            hideDefaultViewButtons
            inner={
              isForm ? (
                <>
                  <Button
                    id="toolbar-save"
                    className="save"
                    aria-label={intl.formatMessage(messages.save)}
                    onClick={() => formRef.current?.onSubmit()}
                  >
                    <Icon
                      name={saveSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.save)}
                    />
                  </Button>
                  <Button
                    className="cancel"
                    aria-label={intl.formatMessage(messages.cancel)}
                    onClick={closeForm}
                  >
                    <Icon
                      name={clearSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.cancel)}
                    />
                  </Button>
                </>
              ) : view === 'keys' ? (
                <Button
                  id="toolbar-back-to-clients"
                  aria-label={intl.formatMessage(messages.title)}
                  onClick={() => setView('list')}
                >
                  <Icon
                    name={backSVG}
                    className="circled"
                    size="30px"
                    title={intl.formatMessage(messages.title)}
                  />
                </Button>
              ) : (
                <>
                  <Button
                    id="toolbar-keys"
                    aria-label={intl.formatMessage(messages.keys)}
                    onClick={() => setView('keys')}
                  >
                    <Icon
                      name={keySVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.keys)}
                    />
                  </Button>
                  <Button
                    id="toolbar-add"
                    aria-label={intl.formatMessage(messages.add)}
                    onClick={() => {
                      setEditing(null);
                      setError(null);
                      setView('add');
                    }}
                  >
                    <Icon
                      name={addSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.add)}
                    />
                  </Button>
                  {/* A router link, not an anchor: an `href` here left the
                      toolbar's back button reloading the whole application
                      to reach a route Volto already has. */}
                  <Link className="item" to="/controlpanel">
                    <Icon
                      name={backSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.back)}
                    />
                  </Link>
                </>
              )
            }
          />,
          document.getElementById('toolbar') as HTMLElement,
        )}
    </div>
  );
};

export default ClientsControlPanel;
