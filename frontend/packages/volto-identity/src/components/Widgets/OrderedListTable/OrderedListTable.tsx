/**
 * An ordered list, edited as a table.
 *
 * The providers control panel's list, for a field: one row per entry in the
 * order the value keeps them, a handle to drag a row by, an Edit and a Delete
 * on every row, and a button to add one more. What an entry *is* comes from a
 * schema, and Volto's own `ModalForm` renders it, so nothing here lays out an
 * input: an address gets Volto's email widget because its field is an
 * `Email`, not because this component knows.
 *
 * Two widgets are built on it, and they differ only in what an entry is: a
 * string (`OrderedStringListWidget`) or an object
 * (`OrderedObjectListWidget`).
 *
 * **Nothing is saved here.** Every action changes the field's value, and the
 * content form saves it or does not. Deleting still asks first: a row removed
 * by mistake can otherwise only be recovered by cancelling every other change
 * on the form with it.
 *
 * **The dialog's submit stops at this component.** `ModalForm` renders into a
 * portal, and React delivers a portal's events to its React ancestors, so
 * pressing Enter in a dialog field would also submit the content form this
 * widget sits in.
 *
 * The drag library is one of Volto's lazy libraries. Until it has loaded the
 * table renders without handles, exactly as `ProvidersTable` does.
 * @module components/Widgets/OrderedListTable
 */
import React, { useState } from 'react';
import type { CSSProperties, ReactNode, Ref } from 'react';
import { Button, Table } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import FormFieldWrapper from '@plone/volto/components/manage/Widgets/FormFieldWrapper';
import ModalForm from '@plone/volto/components/manage/Form/ModalForm';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import { applySchemaDefaults } from '@plone/volto/helpers/Blocks/Blocks';
import { useLazyLibs } from '@plone/volto/helpers/Loadable/Loadable';

import addSVG from '@plone/volto/icons/add.svg';
import deleteSVG from '@plone/volto/icons/delete.svg';
import dragSVG from '@plone/volto/icons/drag.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';

import ConfirmModal from '../../ControlPanel/ConfirmModal';
import { DND_LIBRARIES } from '../../ControlPanel/ProvidersTable';
import { cellText, movedRows, rowKeys } from '../../../helpers/orderedList';
import type { ItemSchema, Row } from '../../../helpers/orderedList';

import './OrderedListTable.scss';

const messages = defineMessages({
  columnOrder: { id: 'Order', defaultMessage: 'Order' },
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  move: { id: 'Move {title}', defaultMessage: 'Move {title}' },
  edit: { id: 'Edit', defaultMessage: 'Edit' },
  delete: { id: 'Delete', defaultMessage: 'Delete' },
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

export type OrderedListTableProps = {
  /** The field's id, as `Field` hands it to a widget. */
  id: string;
  /** The field's title, used when the item schema has none. */
  title?: string;
  isDisabled?: boolean;
  /** The entries, in order. */
  rows: Row[];
  /** What one entry is. The dialog is built from it. */
  schema: ItemSchema;
  /** The schema fields shown as columns, in order. */
  columns: string[];
  /** Given every entry, in order, after any change. */
  onChangeRows: (rows: Row[]) => void;
  /**
   * An objection to an entry about to be stored, shown in the dialog, or
   * nothing. `index` is the entry being edited, or `null` for a new one.
   */
  validate?: (row: Row, index: number | null) => string | undefined;
  /** Everything else `Field` passes, for the label, help and errors. */
  [key: string]: unknown;
};

/** The loaded libraries, keyed as `config.settings.loadables` names them. */
type Libraries = Record<string, any>;

/** What every row needs from the table around it. */
type Shared = {
  schema: ItemSchema;
  columns: string[];
  disabled: boolean;
  edit: (index: number) => void;
  remove: (index: number) => void;
};

type RowProps = {
  row: Row;
  index: number;
  rowKey: string;
  shared: Shared;
};

/**
 * How an entry is named to a screen reader and in the delete question.
 *
 * @param schema What an entry is.
 * @param columns The fields shown as columns.
 * @param row The entry.
 * @param index Its position.
 * @returns Its first column's text, or the item title and its position when
 *   that is empty.
 */
function labelOf(
  schema: ItemSchema,
  columns: string[],
  row: Row,
  index: number,
): string {
  const first = columns[0];
  const text = first ? cellText(schema.properties[first], row[first]) : '';
  return text || `${schema.title ?? ''} #${index + 1}`.trim();
}

/** The table around the rows, which is the same whether or not they drag. */
const Frame = ({
  schema,
  columns,
  children,
}: {
  schema: ItemSchema;
  columns: string[];
  children: ReactNode;
}) => {
  const intl = useIntl();
  return (
    <Table compact className="identity-ordered-list__table">
      <Table.Header>
        <Table.Row>
          <Table.HeaderCell
            collapsing
            aria-label={intl.formatMessage(messages.columnOrder)}
          />
          {columns.map((name) => (
            <Table.HeaderCell key={name}>
              {schema.properties[name]?.title ?? name}
            </Table.HeaderCell>
          ))}
          <Table.HeaderCell textAlign="right">
            {intl.formatMessage(messages.columnActions)}
          </Table.HeaderCell>
        </Table.Row>
      </Table.Header>
      <Table.Body>{children}</Table.Body>
    </Table>
  );
};

/**
 * One entry's row.
 *
 * A plain `tr` rather than Semantic's `Table.Row`, which does not pass a ref
 * on: the drag library measures the row's own node.
 */
const EntryRow = ({
  row,
  index,
  rowKey,
  shared,
  handle = null,
  rowRef,
  style,
  dragging = false,
}: RowProps & {
  handle?: ReactNode;
  rowRef?: Ref<HTMLTableRowElement>;
  style?: CSSProperties;
  dragging?: boolean;
}) => {
  const intl = useIntl();
  const { schema, columns, disabled, edit, remove } = shared;
  return (
    <tr
      ref={rowRef}
      style={style}
      data-row={rowKey}
      className={dragging ? 'identity-ordered-list__dragging' : undefined}
    >
      <td className="collapsing">{handle}</td>
      {columns.map((name) => (
        <td key={name}>{cellText(schema.properties[name], row[name])}</td>
      ))}
      <td className="right aligned collapsing">
        {/* `type="button"` on both: a button's default type is submit, and
            this one sits inside the content form. */}
        <Button
          type="button"
          basic
          icon
          disabled={disabled}
          aria-label={intl.formatMessage(messages.edit)}
          title={intl.formatMessage(messages.edit)}
          onClick={() => edit(index)}
        >
          <Icon name={pencilSVG} size="20px" />
        </Button>
        <Button
          type="button"
          basic
          icon
          disabled={disabled}
          data-action="delete"
          aria-label={intl.formatMessage(messages.delete)}
          title={intl.formatMessage(messages.delete)}
          onClick={() => remove(index)}
        >
          <Icon name={deleteSVG} size="20px" />
        </Button>
      </td>
    </tr>
  );
};

/** A row that drags by its handle. */
const SortableRow = ({
  libraries,
  ...props
}: RowProps & { libraries: Libraries }) => {
  const intl = useIntl();
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = libraries.dndKitSortable.useSortable({ id: props.rowKey });
  const label = intl.formatMessage(messages.move, {
    title: labelOf(
      props.shared.schema,
      props.shared.columns,
      props.row,
      props.index,
    ),
  });
  return (
    <EntryRow
      {...props}
      rowRef={setNodeRef}
      // Translate rather than Transform: a row stretched to the height of
      // the one it passes over reads as a glitch.
      style={{
        transform: libraries.dndKitUtilities.CSS.Translate.toString(transform),
        transition,
      }}
      dragging={isDragging}
      handle={
        <button
          type="button"
          ref={setActivatorNodeRef}
          {...attributes}
          {...listeners}
          className="identity-ordered-list__handle"
          aria-label={label}
          title={label}
        >
          <Icon name={dragSVG} size="20px" />
        </button>
      }
    />
  );
};

/** The rows, once the drag library has loaded. */
const SortableRows = ({
  libraries,
  rows,
  keys,
  shared,
  onMove,
}: {
  libraries: Libraries;
  rows: Row[];
  keys: string[];
  shared: Shared;
  onMove: (moved: string, target: string | null) => void;
}) => {
  const {
    DndContext,
    KeyboardSensor,
    PointerSensor,
    closestCenter,
    useSensor,
    useSensors,
  } = libraries.dndKitCore;
  const {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
  } = libraries.dndKitSortable;
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={({ active, over }: { active: any; over: any }) =>
        onMove(String(active.id), over ? String(over.id) : null)
      }
    >
      <SortableContext items={keys} strategy={verticalListSortingStrategy}>
        <Frame schema={shared.schema} columns={shared.columns}>
          {rows.map((row, index) => (
            <SortableRow
              key={keys[index]}
              libraries={libraries}
              row={row}
              index={index}
              rowKey={keys[index]}
              shared={shared}
            />
          ))}
        </Frame>
      </SortableContext>
    </DndContext>
  );
};

const OrderedListTable: React.FC<OrderedListTableProps> = (props) => {
  // What is not the table's goes to `FormFieldWrapper`. `columns` in
  // particular must not: the wrapper reads a prop of that name as its layout
  // width, and drops the label for anything but 2.
  const { rows, schema, columns, onChangeRows, validate, ...field } = props;
  const { isDisabled } = props;
  const intl = useIntl();
  const libraries: Libraries = useLazyLibs(DND_LIBRARIES);
  const ready = DND_LIBRARIES.every((name) => libraries[name]);

  // Which entry the dialog is open on: its position, `'new'` for one being
  // added, or null when the dialog is closed.
  const [editing, setEditing] = useState<number | 'new' | null>(null);
  // Which entry the delete question is being asked about, or null.
  const [deleting, setDeleting] = useState<number | null>(null);
  const [objection, setObjection] = useState<string | undefined>(undefined);

  const disabled = Boolean(isDisabled);
  const keys = rowKeys(rows);
  const item = schema.title || props.title || '';

  const close = () => {
    setEditing(null);
    setObjection(undefined);
  };

  const onSubmit = (data: Row) => {
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

  const onConfirmDelete = () => {
    const index = deleting;
    setDeleting(null);
    if (index !== null) {
      onChangeRows(rows.filter((_, position) => position !== index));
    }
  };

  const shared: Shared = {
    schema,
    columns,
    disabled,
    edit: setEditing,
    remove: setDeleting,
  };

  let table: ReactNode;
  if (!rows.length) {
    table = (
      <Frame schema={schema} columns={columns}>
        <tr>
          <td
            colSpan={columns.length + 2}
            className="identity-ordered-list__empty"
          >
            {intl.formatMessage(messages.empty)}
          </td>
        </tr>
      </Frame>
    );
  } else if (ready && !disabled) {
    table = (
      <SortableRows
        libraries={libraries}
        rows={rows}
        keys={keys}
        shared={shared}
        onMove={(moved, target) => {
          const next = movedRows(rows, moved, target);
          // A drop that changes nothing changes nothing.
          if (next) {
            onChangeRows(next);
          }
        }}
      />
    );
  } else {
    table = (
      <Frame schema={schema} columns={columns}>
        {rows.map((row, index) => (
          <EntryRow
            key={keys[index]}
            row={row}
            index={index}
            rowKey={keys[index]}
            shared={shared}
          />
        ))}
      </Frame>
    );
  }

  const addLabel = intl.formatMessage(messages.add, { item });

  return (
    <div className="identity-ordered-list">
      <FormFieldWrapper {...field} noForInFieldLabel>
        <Button
          type="button"
          basic
          icon
          disabled={disabled}
          className="identity-ordered-list__add"
          aria-label={addLabel}
          title={addLabel}
          onClick={() => setEditing('new')}
        >
          <Icon name={addSVG} size="20px" />
        </Button>
      </FormFieldWrapper>
      {table}
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
        header={
          deleting !== null && rows[deleting]
            ? labelOf(schema, columns, rows[deleting], deleting)
            : ''
        }
        content={intl.formatMessage(messages.confirmDelete)}
        onCancel={() => setDeleting(null)}
        onConfirm={onConfirmDelete}
      />
    </div>
  );
};

export default OrderedListTable;
