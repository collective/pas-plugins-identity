/**
 * The providers control panel.
 *
 * Shaped after `volto-light-theme`'s Themes panel: a table of what exists,
 * with the add and save actions living in the toolbar rather than inline, and
 * the form itself rendered by Volto's own `Form` from a schema. Nothing here
 * lays out an input; the driver describes its fields and Volto renders them,
 * which is what keeps this panel looking like every other one.
 * @module components/ControlPanel/ProvidersControlPanel
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Button, Container, Segment, Table } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';
import { toast } from 'react-toastify';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import Toast from '@plone/volto/components/manage/Toast/Toast';
import { Form } from '@plone/volto/components/manage/Form';
import {
  getControlpanel,
  updateControlpanel,
} from '@plone/volto/actions/controlpanels/controlpanels';

import addSVG from '@plone/volto/icons/add.svg';
import backSVG from '@plone/volto/icons/back.svg';
import clearSVG from '@plone/volto/icons/clear.svg';
import deleteSVG from '@plone/volto/icons/delete.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';
import worldSVG from '@plone/volto/icons/world.svg';
import saveSVG from '@plone/volto/icons/save.svg';
import configurationSVG from '@plone/volto/icons/configuration.svg';

import {
  createProvider,
  deleteProvider,
  listDrivers,
  listProviders,
  testProvider,
  updateProvider,
} from '../../actions';
import { fromRows, toRows } from '../../helpers/propertymap';
import {
  fromFormData,
  providerSchema,
  toFormData,
} from '../../helpers/providerSchema';
import type { ConfiguredProvider, Driver } from '../../types';

/**
 * The configlet id, which is also the name the site-wide settings are served
 * under at `@controlpanels/<id>`.
 */
const CONFIGLET_ID = 'identity-providers';

const messages = defineMessages({
  title: { id: 'Identity providers', defaultMessage: 'Identity providers' },
  add: { id: 'Add provider', defaultMessage: 'Add provider' },
  back: { id: 'Back', defaultMessage: 'Back' },
  save: { id: 'Save', defaultMessage: 'Save' },
  cancel: { id: 'Cancel', defaultMessage: 'Cancel' },
  edit: { id: 'Edit', defaultMessage: 'Edit' },
  test: { id: 'Test connection', defaultMessage: 'Test connection' },
  delete: { id: 'Delete', defaultMessage: 'Delete' },
  saved: { id: 'Changes saved', defaultMessage: 'Changes saved' },
  deleted: { id: 'Provider deleted', defaultMessage: 'Provider deleted' },
  settings: { id: 'Settings', defaultMessage: 'Settings' },
  noCallback: {
    id: 'No login callback URL is configured',
    defaultMessage:
      'No login callback URL is configured, so no provider can complete a ' +
      'sign-in. Set it under Settings.',
  },
  error: { id: 'Error', defaultMessage: 'Error' },
  empty: {
    id: 'No providers are configured yet.',
    defaultMessage: 'No providers are configured yet.',
  },
  noDrivers: {
    id: 'No drivers are installed.',
    defaultMessage:
      'No drivers are installed, so there is nothing to configure. Install ' +
      'an add-on that registers one.',
  },
  confirmDelete: {
    id: 'Delete this provider?',
    defaultMessage:
      'Delete this provider? Identities already linked through it keep the ' +
      'stored id and stop resolving.',
  },
});

const ProvidersControlPanel: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const { pathname } = useLocation();
  const formRef = useRef<any>(null);

  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [editingSettings, setEditingSettings] = useState(false);
  // Which driver the add form is currently on. The schema depends on it, so
  // it is tracked as the form changes rather than read at submit time.
  const [draftDriver, setDraftDriver] = useState<string | undefined>(undefined);
  const [error, setError] = useState<unknown>(null);

  const providers = useSelector((state: any) => state.configuredProviders) as {
    data?: ConfiguredProvider[];
    loading?: boolean;
  };
  const drivers = useSelector((state: any) => state.identityDrivers) as {
    data?: Driver[];
  };
  const check = useSelector((state: any) => state.providerTest);
  // The site-wide settings, served by the same configlet id. The callback
  // URL lives here rather than on a provider: it is one route in the
  // frontend, registered identically with every provider.
  const settings = useSelector(
    (state: any) => state.controlpanels?.controlpanel,
  );

  const items = providers?.data ?? [];
  // Memoized because the schema is built from it: a fresh [] on every render
  // would rebuild the schema on every render, and Form would lose its state.
  const driverList = useMemo(() => drivers?.data ?? [], [drivers?.data]);

  const refresh = () => {
    dispatch(listProviders());
  };

  useEffect(() => {
    dispatch(listProviders());
    dispatch(listDrivers());
    dispatch(getControlpanel(CONFIGLET_ID));
  }, [dispatch]);

  useEffect(() => {
    if (check?.loaded && check?.data) {
      const result = check.data;
      if (result.ok) {
        toast.success(
          <Toast
            success
            title={intl.formatMessage(messages.test)}
            content={`Reached ${result.token_endpoint}${
              result.has_jwks ? '' : ' (no key set published)'
            }`}
          />,
        );
      } else {
        toast.error(
          <Toast
            error
            title={intl.formatMessage(messages.test)}
            content={result.error}
          />,
        );
      }
    }
  }, [check?.loaded, check?.data, intl]);

  const fail = (err: any) => {
    setError(err);
    toast.error(
      <Toast
        error
        title={intl.formatMessage(messages.error)}
        content={err?.response?.body?.error?.message ?? String(err)}
      />,
    );
  };

  const succeed = (message: string) => {
    toast.success(<Toast success title={message} />);
    closeForm();
    refresh();
  };

  function closeForm() {
    setAdding(false);
    setEditing(null);
    setEditingSettings(false);
    setDraftDriver(undefined);
    setError(null);
  }

  const current = editing
    ? items.find((provider) => provider.id === editing)
    : undefined;
  const isForm = adding || editing !== null || editingSettings;
  const callbackUrl = settings?.data?.callback_url;

  const schema = useMemo(
    () =>
      providerSchema(
        driverList,
        adding ? draftDriver : current?.driver,
        adding,
      ),
    [driverList, adding, draftDriver, current?.driver],
  );

  const formData = useMemo(
    () => toFormData(adding ? undefined : current, toRows),
    [adding, current],
  );

  const onSubmit = (data: Record<string, unknown>) => {
    const payload = fromFormData(data, fromRows);
    if (adding) {
      (dispatch(createProvider(payload)) as any)
        .then(() => succeed(intl.formatMessage(messages.saved)))
        .catch(fail);
      return;
    }
    const { id: _id, ...rest } = payload;
    (dispatch(updateProvider(editing as string, rest)) as any)
      .then(() => succeed(intl.formatMessage(messages.saved)))
      .catch(fail);
  };

  const onSaveSettings = (data: Record<string, unknown>) => {
    const { '@id': _atId, ...values } = data ?? {};
    (dispatch(updateControlpanel(settings['@id'], values)) as any)
      .then(() => {
        succeed(intl.formatMessage(messages.saved));
        dispatch(getControlpanel(CONFIGLET_ID));
      })
      .catch(fail);
  };

  const onDelete = (provider: ConfiguredProvider) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(intl.formatMessage(messages.confirmDelete))) {
      return;
    }
    (dispatch(deleteProvider(provider.id)) as any)
      .then(() => succeed(intl.formatMessage(messages.deleted)))
      .catch(fail);
  };

  return (
    <div id="page-controlpanel" className="identity-controlpanel">
      <Helmet title={intl.formatMessage(messages.title)} />
      <Container>
        {isForm ? (
          <Form
            ref={formRef}
            title={
              editingSettings
                ? intl.formatMessage(messages.settings)
                : adding
                  ? intl.formatMessage(messages.add)
                  : current?.title || current?.id
            }
            // The settings schema comes from the backend, which already
            // serves it for the Classic form; nothing is described twice.
            schema={editingSettings ? settings?.schema : schema}
            formData={editingSettings ? settings?.data : formData}
            requestError={error}
            onSubmit={editingSettings ? onSaveSettings : onSubmit}
            onCancel={closeForm}
            onChangeFormData={(data: Record<string, unknown>) => {
              // The driver decides which settings exist, so choosing one has
              // to rebuild the schema rather than wait for submit.
              if (adding && data.driver !== draftDriver) {
                setDraftDriver(data.driver as string);
              }
            }}
            hideActions
          />
        ) : (
          <Segment.Group raised>
            <Segment className="primary">
              {intl.formatMessage(messages.title)}
            </Segment>
            {settings?.data && !callbackUrl ? (
              // Without it every sign-in fails at the last step with an
              // error only the log shows. Better said here, before anyone
              // configures a provider and wonders why it does not work.
              <Segment className="identity-controlpanel__warning" secondary>
                <strong>{intl.formatMessage(messages.noCallback)}</strong>
              </Segment>
            ) : null}
            <Segment>
              {items.length ? (
                <Table selectable compact>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell>Title</Table.HeaderCell>
                      <Table.HeaderCell>Id</Table.HeaderCell>
                      <Table.HeaderCell>Driver</Table.HeaderCell>
                      <Table.HeaderCell>Enabled</Table.HeaderCell>
                      <Table.HeaderCell textAlign="right">
                        Actions
                      </Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {items.map((provider) => (
                      <Table.Row
                        key={provider['@id']}
                        data-provider={provider.id}
                      >
                        <Table.Cell>{provider.title || provider.id}</Table.Cell>
                        <Table.Cell>
                          <code>{provider.id}</code>
                        </Table.Cell>
                        <Table.Cell>{provider.driver}</Table.Cell>
                        <Table.Cell>
                          {provider.enabled ? 'Yes' : 'No'}
                        </Table.Cell>
                        <Table.Cell textAlign="right">
                          <Button
                            basic
                            icon
                            aria-label={intl.formatMessage(messages.edit)}
                            title={intl.formatMessage(messages.edit)}
                            onClick={() => setEditing(provider.id)}
                          >
                            <Icon name={pencilSVG} size="20px" />
                          </Button>
                          <Button
                            basic
                            icon
                            aria-label={intl.formatMessage(messages.test)}
                            title={intl.formatMessage(messages.test)}
                            onClick={() => dispatch(testProvider(provider.id))}
                          >
                            <Icon name={worldSVG} size="20px" />
                          </Button>
                          <Button
                            basic
                            icon
                            data-action="delete"
                            aria-label={intl.formatMessage(messages.delete)}
                            title={intl.formatMessage(messages.delete)}
                            onClick={() => onDelete(provider)}
                          >
                            <Icon name={deleteSVG} size="20px" />
                          </Button>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              ) : (
                <p className="identity-controlpanel__empty">
                  {intl.formatMessage(
                    driverList.length ? messages.empty : messages.noDrivers,
                  )}
                </p>
              )}
            </Segment>
          </Segment.Group>
        )}
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
              ) : (
                <>
                  <Button
                    id="toolbar-settings"
                    aria-label={intl.formatMessage(messages.settings)}
                    onClick={() => setEditingSettings(true)}
                  >
                    <Icon
                      name={configurationSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.settings)}
                    />
                  </Button>
                  {driverList.length ? (
                    <Button
                      id="toolbar-add"
                      aria-label={intl.formatMessage(messages.add)}
                      onClick={() => setAdding(true)}
                    >
                      <Icon
                        name={addSVG}
                        className="circled"
                        size="30px"
                        title={intl.formatMessage(messages.add)}
                      />
                    </Button>
                  ) : null}
                  <a className="item" href="/controlpanel">
                    <Icon
                      name={backSVG}
                      className="circled"
                      size="30px"
                      title={intl.formatMessage(messages.back)}
                    />
                  </a>
                </>
              )
            }
          />,
          document.getElementById('toolbar') as HTMLElement,
        )}
    </div>
  );
};

export default ProvidersControlPanel;
