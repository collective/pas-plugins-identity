/**
 * An ordered list, edited as a table.
 *
 * One row per entry in the order the value keeps them, a handle to drag a row
 * by, an Edit and a Delete on every row, and a button to add one more. What
 * an entry *is* comes from a schema, and Volto's own `ModalForm` renders it,
 * so nothing here lays out an input: an address gets Volto's email widget
 * because its field is an `Email`, not because this component knows.
 *
 * Two widgets are built on it, and they differ only in what an entry is: a
 * string (`OrderedStringListWidget`) or an object
 * (`OrderedObjectListWidget`).
 *
 * **The table is react-aria's,** through `@plone/components` where it wraps
 * one: its `TableHeader`, `Row` and `Column` add the drag column and the drag
 * handle, and `useDragAndDrop` reorders with a pointer, the keyboard or a
 * screen reader alike. react-aria names the handle ("Drag …") and announces a
 * move in the page's language, which is why the table sits in an
 * `I18nProvider` set to the locale `react-intl` already has. Each row tells it
 * what to call the entry, through `textValue`.
 *
 * **Nothing is saved here.** Every action changes the field's value, and the
 * content form saves it or does not. Deleting still asks first: a row removed
 * by mistake can otherwise only be recovered by cancelling every other change
 * on the form with it. The question is asked about an entry's key, not its
 * position, so a list that changes while it is open cannot make it delete a
 * different entry.
 *
 * **The dialog's submit stops at this component.** `ModalForm` renders into a
 * portal, and React delivers a portal's events to its React ancestors, so
 * pressing Enter in a dialog field would also submit the content form this
 * widget sits in.
 * @module components/Widgets/OrderedListTable
 */
import React, { useState } from 'react';
import type { ReactNode } from 'react';
import { defineMessages, useIntl } from 'react-intl';
import {
  Cell,
  I18nProvider,
  Table,
  TableBody,
  useDragAndDrop,
} from 'react-aria-components';
import { Button, Column, Row, TableHeader } from '@plone/components';

import FormFieldWrapper from '@plone/volto/components/manage/Widgets/FormFieldWrapper';
import ModalForm from '@plone/volto/components/manage/Form/ModalForm';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import { applySchemaDefaults } from '@plone/volto/helpers/Blocks/Blocks';

import addSVG from '@plone/volto/icons/add.svg';
import deleteSVG from '@plone/volto/icons/delete.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';

import ConfirmModal from '../../ControlPanel/ConfirmModal';
import { cellText, reorderedRows, rowKeys } from '../../../helpers/orderedList';
import type {
  DropPosition,
  ItemSchema,
  Row as Entry,
} from '../../../helpers/orderedList';

// `@plone/components` ships its CSS apart from its components.
import '@plone/components/src/styles/basic/Table.css';
import './OrderedListTable.scss';

const messages = defineMessages({
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  editRow: {
    id: 'ordered-list-edit-row',
    defaultMessage: 'Edit {title}',
  },
  deleteRow: {
    id: 'ordered-list-delete-row',
    defaultMessage: 'Delete {title}',
  },
  add: { id: 'Add {item}', defaultMessage: 'Add {item}' },
  editItem: { id: 'Edit {item}', defaultMessage: 'Edit {item}' },
  empty: {
    id: 'ordered-list-empty',
    defaultMessage: 'Nothing has been added yet.',
  },
  confirmDelete: {
    id: 'ordered-list-confirm-delete',
    defaultMessage:
      'Remove this entry from the list? It is gone once the form is saved.',
  },
});

/** The id of the column the actions sit in, which no schema field can take. */
const ACTIONS = '@actions';

export type OrderedListTableProps = {
  /** The field's id, as `Field` hands it to a widget. */
  id: string;
  /** The field's title, used when the item schema has none. */
  title?: string;
  isDisabled?: boolean;
  /** The entries, in order. */
  rows: Entry[];
  /** What one entry is. The dialog is built from it. */
  schema: ItemSchema;
  /** The schema fields shown as columns, in order. */
  columns: string[];
  /** Given every entry, in order, after any change. */
  onChangeRows: (rows: Entry[]) => void;
  /**
   * An objection to an entry about to be stored, shown in the dialog, or
   * nothing. `index` is the entry being edited, or `null` for a new one.
   */
  validate?: (row: Entry, index: number | null) => string | undefined;
  /** Everything else `Field` passes, for the label, help and errors. */
  [key: string]: unknown;
};

/** A column of the table: a schema field, or the actions. */
type TableColumn = { id: string; name: string; isRowHeader?: boolean };

/** A row of the table, as react-aria's collection takes it. */
type TableItem = {
  id: string;
  index: number;
  label: string;
  entry: Entry;
};

/**
 * How an entry is named: to a screen reader, on its buttons and in the
 * delete question.
 *
 * @param schema What an entry is.
 * @param columns The fields shown as columns.
 * @param row The entry.
 * @param index Its position.
 * @returns Its first column's text, or the item title and its position when
 *   that is empty.
 */
export function labelOf(
  schema: ItemSchema,
  columns: string[],
  row: Entry,
  index: number,
): string {
  const first = columns[0];
  const text = first ? cellText(schema.properties[first], row[first]) : '';
  return text || `${schema.title ?? ''} #${index + 1}`.trim();
}

/**
 * The locale react-aria should speak, from the one `react-intl` has.
 *
 * Volto's locales are written `pt_BR` or `pt-br`; react-aria wants a BCP 47
 * tag.
 *
 * @param locale The `react-intl` locale.
 * @returns The same locale as a BCP 47 tag.
 */
export function ariaLocale(locale: string): string {
  const [language, region] = locale.replace('_', '-').split('-');
  return region ? `${language}-${region.toUpperCase()}` : language;
}

const OrderedListTable: React.FC<OrderedListTableProps> = (props) => {
  // What is not the table's goes to `FormFieldWrapper`. `columns` in
  // particular must not: the wrapper reads a prop of that name as its layout
  // width, and drops the label for anything but 2.
  const { rows, schema, columns, onChangeRows, validate, ...field } = props;
  const { isDisabled } = props;
  const intl = useIntl();

  // Which entry the dialog is open on: its position, `'new'` for one being
  // added, or null when the dialog is closed.
  const [editing, setEditing] = useState<number | 'new' | null>(null);
  // Which entry the delete question is being asked about, by key, or null.
  const [deleting, setDeleting] = useState<string | null>(null);
  const [objection, setObjection] = useState<string | undefined>(undefined);

  const disabled = Boolean(isDisabled);
  const keys = rowKeys(rows);
  const item = schema.title || props.title || '';

  const items: TableItem[] = rows.map((entry, index) => ({
    id: keys[index],
    index,
    label: labelOf(schema, columns, entry, index),
    entry,
  }));
  const tableColumns: TableColumn[] = [
    ...columns.map((name, position) => ({
      id: name,
      name: schema.properties[name]?.title ?? name,
      isRowHeader: position === 0,
    })),
    { id: ACTIONS, name: intl.formatMessage(messages.columnActions) },
  ];

  const { dragAndDropHooks } = useDragAndDrop({
    getItems: (dragged) =>
      [...dragged].map((key) => ({
        'text/plain': items.find((row) => row.id === key)?.label ?? '',
      })),
    onReorder: (event) => {
      const next = reorderedRows(
        rows,
        [...event.keys].map(String),
        String(event.target.key),
        event.target.dropPosition as DropPosition,
      );
      // A drop that changes nothing changes nothing.
      if (next) {
        onChangeRows(next);
      }
    },
  });

  const close = () => {
    setEditing(null);
    setObjection(undefined);
  };

  const onSubmit = (data: Entry) => {
    const index = editing === 'new' ? null : editing;
    const problem = validate?.(data, index);
    if (problem) {
      setObjection(problem);
      return;
    }
    onChangeRows(
      index === null
        ? [...rows, data]
        : rows.map((row, position) => (position === index ? data : row)),
    );
    close();
  };

  const deletingItem = items.find((row) => row.id === deleting);

  const onConfirmDelete = () => {
    setDeleting(null);
    // Gone already, by some other change while the question was open: there
    // is nothing left to delete, and certainly not whatever took its place.
    if (deletingItem) {
      onChangeRows(
        rows.filter((_, position) => position !== deletingItem.index),
      );
    }
  };

  const renderCell = (row: TableItem, column: TableColumn): ReactNode => {
    if (column.id !== ACTIONS) {
      return cellText(schema.properties[column.id], row.entry[column.id]);
    }
    const edit = intl.formatMessage(messages.editRow, { title: row.label });
    const remove = intl.formatMessage(messages.deleteRow, { title: row.label });
    return (
      <div className="identity-ordered-list__actions">
        <Button
          className="identity-ordered-list__action"
          isDisabled={disabled}
          aria-label={edit}
          onPress={() => setEditing(row.index)}
        >
          <Icon name={pencilSVG} size="20px" title={edit} />
        </Button>
        <Button
          className="identity-ordered-list__action"
          data-action="delete"
          isDisabled={disabled}
          aria-label={remove}
          onPress={() => setDeleting(row.id)}
        >
          <Icon name={deleteSVG} size="20px" title={remove} />
        </Button>
      </div>
    );
  };

  const addLabel = intl.formatMessage(messages.add, { item });

  return (
    <div className="identity-ordered-list">
      <FormFieldWrapper {...field} noForInFieldLabel>
        <Button
          className="identity-ordered-list__add"
          isDisabled={disabled}
          aria-label={addLabel}
          onPress={() => setEditing('new')}
        >
          <Icon name={addSVG} size="20px" title={addLabel} />
        </Button>
      </FormFieldWrapper>
      <I18nProvider locale={ariaLocale(intl.locale)}>
        <Table
          aria-label={String(props.title || item)}
          className="react-aria-Table identity-ordered-list__table"
          // No reordering a list nobody may change.
          dragAndDropHooks={disabled ? undefined : dragAndDropHooks}
        >
          <TableHeader columns={tableColumns}>
            {(column: TableColumn) => (
              <Column
                id={column.id}
                isRowHeader={column.isRowHeader}
                className={
                  column.id === ACTIONS
                    ? 'react-aria-Column identity-ordered-list__actions-header'
                    : undefined
                }
              >
                {column.name}
              </Column>
            )}
          </TableHeader>
          <TableBody
            items={items}
            renderEmptyState={() => (
              <span className="identity-ordered-list__empty">
                {intl.formatMessage(messages.empty)}
              </span>
            )}
          >
            {(row: TableItem) => (
              <Row
                id={row.id}
                columns={tableColumns}
                textValue={row.label}
                data-row={row.id}
              >
                {(column: TableColumn) => (
                  <Cell>{renderCell(row, column)}</Cell>
                )}
              </Row>
            )}
          </TableBody>
        </Table>
      </I18nProvider>
      {/* See the module docstring: the dialog's submit must not reach the
          content form. */}
      <div onSubmit={(event) => event.stopPropagation()}>
        {editing !== null ? (
          <ModalForm
            // Remounted per entry: `ModalForm` keeps what it was given in
            // state and only merges later changes in, so the previous
            // entry's fields would survive into the next one.
            key={String(editing)}
            open
            title={
              editing === 'new'
                ? addLabel
                : intl.formatMessage(messages.editItem, { item })
            }
            schema={schema}
            formData={
              editing === 'new'
                ? applySchemaDefaults({ data: {}, schema, intl })
                : rows[editing]
            }
            submitError={objection}
            onSubmit={onSubmit}
            onCancel={close}
          />
        ) : null}
      </div>
      <ConfirmModal
        open={deleting !== null}
        header={deletingItem?.label ?? ''}
        content={intl.formatMessage(messages.confirmDelete)}
        onCancel={() => setDeleting(null)}
        onConfirm={onConfirmDelete}
      />
    </div>
  );
};

export default OrderedListTable;
