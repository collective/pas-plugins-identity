/**
 * The providers control panel's list.
 *
 * One row per provider, in the order the login page offers their buttons, and
 * dragged by a handle to change that order. What the list does with a drop is
 * its caller's business: it reports the new order, and saving it -- or putting
 * the row back when that fails -- happens in the panel.
 *
 * **The table is react-aria's,** through `@plone/components`, as the list
 * widgets' is: its `TableHeader` and `Row` add the drag column and handle, and
 * `useDragAndDrop` reorders with a pointer, the keyboard or a screen reader
 * alike, announcing each move in the page's language. It ships with the
 * add-on, so the handles are there from the first render, server included.
 *
 * Every row's actions are named for the provider they act on, so a screen
 * reader moving through the table hears which row a button belongs to.
 * @module components/ControlPanel/ProvidersTable
 */
import React from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';
import {
  Cell,
  I18nProvider,
  Table,
  TableBody,
  useDragAndDrop,
} from 'react-aria-components';
import { Button, Column, Row, TableHeader } from '@plone/components';

import Icon from '@plone/volto/components/theme/Icon/Icon';

import deleteSVG from '@plone/volto/icons/delete.svg';
import downloadSVG from '@plone/volto/icons/download.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';
import worldSVG from '@plone/volto/icons/world.svg';

import { providerEditUrl } from '../../config/routes';
import type { DropPosition } from '../../helpers/orderedList';
import { reorderedIds } from '../../helpers/providerOrder';
import type { ConfiguredProvider } from '../../types';
import { ariaLocale } from '../Widgets/OrderedListTable/OrderedListTable';

// `@plone/components` ships its CSS apart from its components.
import '@plone/components/src/styles/basic/Table.css';
import './ProvidersTable.scss';

const messages = defineMessages({
  providers: { id: 'Providers', defaultMessage: 'Providers' },
  columnTitle: { id: 'Title', defaultMessage: 'Title' },
  columnId: { id: 'Id', defaultMessage: 'Id' },
  columnDriver: { id: 'Driver', defaultMessage: 'Driver' },
  columnEnabled: { id: 'Enabled', defaultMessage: 'Enabled' },
  columnLogin: { id: 'Login screen', defaultMessage: 'Login screen' },
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  yes: { id: 'Yes', defaultMessage: 'Yes' },
  no: { id: 'No', defaultMessage: 'No' },
  edit: { id: 'provider-row-edit', defaultMessage: 'Edit {title}' },
  test: {
    id: 'provider-row-test',
    defaultMessage: 'Test connection to {title}',
  },
  export: { id: 'provider-row-export', defaultMessage: 'Export {title}' },
  delete: { id: 'provider-row-delete', defaultMessage: 'Delete {title}' },
});

type Props = {
  /** The providers, in the order to show them. */
  providers: ConfiguredProvider[];
  /** Given every provider's id, in the new order, when a row is dropped. */
  onReorder: (providerIds: string[]) => void;
  onTest: (provider: ConfiguredProvider) => void;
  onDelete: (provider: ConfiguredProvider) => void;
  /**
   * Given the provider whose Export action was used. Without it no row
   * offers one: exporting needs a permission of its own.
   */
  onExport?: (provider: ConfiguredProvider) => void;
};

/** The columns, by id. The first names the row. */
type ColumnId = 'title' | 'id' | 'driver' | 'enabled' | 'login' | 'actions';

type TableColumn = { id: ColumnId; name: string; isRowHeader?: boolean };

/** A row of the table, as react-aria's collection takes it. */
type TableItem = { id: string; label: string; provider: ConfiguredProvider };

const ProvidersTable = ({
  providers,
  onReorder,
  onTest,
  onDelete,
  onExport,
}: Props) => {
  const intl = useIntl();
  const yesNo = (value: boolean) =>
    intl.formatMessage(value ? messages.yes : messages.no);

  const items: TableItem[] = providers.map((provider) => ({
    id: provider.id,
    label: provider.title || provider.id,
    provider,
  }));
  const columns: TableColumn[] = [
    {
      id: 'title',
      name: intl.formatMessage(messages.columnTitle),
      isRowHeader: true,
    },
    { id: 'id', name: intl.formatMessage(messages.columnId) },
    { id: 'driver', name: intl.formatMessage(messages.columnDriver) },
    { id: 'enabled', name: intl.formatMessage(messages.columnEnabled) },
    { id: 'login', name: intl.formatMessage(messages.columnLogin) },
    { id: 'actions', name: intl.formatMessage(messages.columnActions) },
  ];

  const { dragAndDropHooks } = useDragAndDrop({
    getItems: (dragged) =>
      [...dragged].map((key) => ({
        'text/plain': items.find((row) => row.id === key)?.label ?? '',
      })),
    onReorder: (event) => {
      const next = reorderedIds(
        items.map((row) => row.id),
        [...event.keys].map(String),
        String(event.target.key),
        event.target.dropPosition as DropPosition,
      );
      // A drop that changes nothing saves nothing.
      if (next) {
        onReorder(next);
      }
    },
  });

  const renderActions = ({ provider, label }: TableItem): ReactNode => {
    const edit = intl.formatMessage(messages.edit, { title: label });
    const test = intl.formatMessage(messages.test, { title: label });
    const exportLabel = intl.formatMessage(messages.export, { title: label });
    const remove = intl.formatMessage(messages.delete, { title: label });
    return (
      <div className="identity-providers__actions">
        {/* A link rather than a button: the edit form is a route, so it can
            be opened in a new tab. */}
        <Link
          to={providerEditUrl(provider.id)}
          className="identity-providers__action"
          aria-label={edit}
        >
          <Icon name={pencilSVG} size="20px" title={edit} />
        </Link>
        <Button
          className="identity-providers__action"
          aria-label={test}
          onPress={() => onTest(provider)}
        >
          <Icon name={worldSVG} size="20px" title={test} />
        </Button>
        {onExport ? (
          <Button
            className="identity-providers__action"
            aria-label={exportLabel}
            onPress={() => onExport(provider)}
          >
            <Icon name={downloadSVG} size="20px" title={exportLabel} />
          </Button>
        ) : null}
        <Button
          className="identity-providers__action"
          data-action="delete"
          aria-label={remove}
          onPress={() => onDelete(provider)}
        >
          <Icon name={deleteSVG} size="20px" title={remove} />
        </Button>
      </div>
    );
  };

  const renderCell = (row: TableItem, column: TableColumn): ReactNode => {
    const { provider } = row;
    switch (column.id) {
      case 'title':
        return row.label;
      case 'id':
        return <code>{provider.id}</code>;
      case 'driver':
        return provider.driver;
      case 'enabled':
        return yesNo(provider.enabled);
      case 'login':
        return yesNo(provider.show_in_login);
      default:
        return renderActions(row);
    }
  };

  return (
    <I18nProvider locale={ariaLocale(intl.locale)}>
      <Table
        aria-label={intl.formatMessage(messages.providers)}
        className="react-aria-Table identity-providers__table"
        dragAndDropHooks={dragAndDropHooks}
      >
        <TableHeader columns={columns}>
          {(column: TableColumn) => (
            <Column
              id={column.id}
              isRowHeader={column.isRowHeader}
              className={
                column.id === 'actions'
                  ? 'react-aria-Column identity-providers__actions-header'
                  : undefined
              }
            >
              {column.name}
            </Column>
          )}
        </TableHeader>
        <TableBody items={items}>
          {(row: TableItem) => (
            <Row
              id={row.id}
              columns={columns}
              textValue={row.label}
              data-provider={row.id}
            >
              {(column: TableColumn) => <Cell>{renderCell(row, column)}</Cell>}
            </Row>
          )}
        </TableBody>
      </Table>
    </I18nProvider>
  );
};

export default ProvidersTable;
