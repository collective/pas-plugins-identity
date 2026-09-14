/**
 * An ordered list of objects, edited as a table.
 *
 * Volto's `object_list` widget edits the same value -- a JSON list of objects
 * an item schema describes -- as a stack of accordions, which shows one entry
 * at a time. This one shows every entry as a row of the columns it is told to
 * show, and opens the whole entry in a dialog.
 *
 * **The item schema** is found the way `object_list` finds it, so a field
 * written for that widget works here unchanged: a `schemaName` naming a
 * registered `schema` utility, or a `schema` prop, either of them a schema or
 * a function returning one. A schema without fieldsets is ignored rather than
 * rendered, so a list whose schema cannot be found still shows its rows
 * instead of taking the whole form down with it.
 *
 * **The columns** are the `columns` prop, a list of the item schema's field
 * names. Without one, every field is a column. A backend picks them through
 * `widgetProps`:
 * `frontendOptions={"widget": "identity_object_list",
 * "widgetProps": {"columns": ["id", "title"]}}`.
 *
 * **Every entry is given an `@id`**, which `object_list` writes too: the rows
 * drag by it, and a value edited here stays one `object_list` can edit.
 * @module components/Widgets/OrderedObjectListWidget
 */
import React from 'react';
import { useIntl } from 'react-intl';
import type { IntlShape } from 'react-intl';

import config from '@plone/volto/registry';

import OrderedListTable from '../OrderedListTable/OrderedListTable';
import { withRowIds } from '../../../helpers/orderedList';
import type { ItemSchema, Row } from '../../../helpers/orderedList';

type SchemaSource =
  | ItemSchema
  | ((args: Record<string, unknown>) => ItemSchema);

export type OrderedObjectListWidgetProps = {
  id: string;
  title: string;
  value?: Row[] | null;
  /** The item schema, or a function building it. */
  schema?: SchemaSource;
  /** The name of a registered `schema` utility building the item schema. */
  schemaName?: string;
  /** The item schema's fields shown as columns, in order. */
  columns?: string[];
  onChange: (id: string, value: Row[]) => void;
  [key: string]: unknown;
};

/** What a list with no usable item schema is edited with: nothing. */
const NO_FIELDS: ItemSchema = {
  fieldsets: [{ id: 'default', title: 'Default', fields: [] }],
  properties: {},
  required: [],
};

/**
 * The item schema for a widget's props.
 *
 * A function is called with the widget's props spread, as `object_list` calls
 * it, and also with `props` and `intl` as keys, which is how
 * `volto-social-media`'s `socialMedia` utility reads them.
 *
 * @param props The widget's props.
 * @param intl The current locale's formatter.
 * @returns The registered utility's schema, else the `schema` prop's, else a
 *   schema with no fields.
 */
export function resolveItemSchema(
  props: OrderedObjectListWidgetProps,
  intl: IntlShape,
): ItemSchema {
  const registered = props.schemaName
    ? config.getUtility({ type: 'schema', name: props.schemaName })?.method
    : undefined;
  const source = (registered ?? props.schema) as SchemaSource | undefined;
  const schema =
    typeof source === 'function' ? source({ ...props, props, intl }) : source;
  return schema && Array.isArray(schema.fieldsets) ? schema : NO_FIELDS;
}

/**
 * The columns a table shows.
 *
 * @param schema The item schema.
 * @param columns The field names asked for, if any.
 * @returns Those names, or every field in the schema when none were asked for.
 */
export function columnsOf(schema: ItemSchema, columns?: string[]): string[] {
  return columns?.length
    ? columns
    : schema.fieldsets.flatMap((fieldset) => fieldset.fields);
}

const OrderedObjectListWidget: React.FC<OrderedObjectListWidgetProps> = (
  props,
) => {
  const { id, value, columns, onChange } = props;
  const intl = useIntl();
  const schema = resolveItemSchema(props, intl);

  return (
    <OrderedListTable
      {...props}
      rows={value ?? []}
      schema={schema}
      columns={columnsOf(schema, columns)}
      onChangeRows={(rows) => onChange(id, withRowIds(rows))}
    />
  );
};

/** What a social link is summarized by: its network, and its title. */
export const SOCIAL_LINK_COLUMNS = ['id', 'title'];

/**
 * The widget, standing in for `volto-social-media`'s.
 *
 * `plonegovbr.socialmedia` asks for `social_media_object_list` on its
 * `social_links` field, with the `socialMedia` schema name, and this package
 * does not own that field to point it anywhere else. So this is registered
 * under that name too, with the two columns a link is recognised by. A
 * `columns` the backend sends still wins.
 */
export const SocialLinksWidget: React.FC<OrderedObjectListWidgetProps> = (
  props,
) => <OrderedObjectListWidget columns={SOCIAL_LINK_COLUMNS} {...props} />;

export default OrderedObjectListWidget;
