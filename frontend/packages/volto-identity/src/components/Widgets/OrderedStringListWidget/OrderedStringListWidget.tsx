/**
 * An ordered list of strings, edited as a table.
 *
 * For a `schema.List` or `schema.Tuple` of text, which Volto otherwise renders
 * as a creatable select. That suits tags, and it does not suit a list whose
 * *order* means something and whose entries are each worth a field of their
 * own. A Profile's `emails` is the case: the first verified address stands
 * for the person, and every entry is an `Email`.
 *
 * The entry's field is the one the backend serialized as the list's `items`,
 * so the dialog asks for an address with Volto's email widget, and validates
 * it, because the value type is `Email`. The column header is that field's
 * title. A list the backend declares `uniqueItems` -- every `Tuple` and `Set`
 * is one -- refuses an entry already on it.
 *
 * The backend asks for it by name:
 * `frontendOptions={"widget": "identity_string_list"}`.
 * @module components/Widgets/OrderedStringListWidget
 */
import React, { useMemo } from 'react';
import { defineMessages, useIntl } from 'react-intl';

import OrderedListTable from '../OrderedListTable/OrderedListTable';
import type { ItemSchema, Row } from '../../../helpers/orderedList';

/** The one field an entry's dialog has. */
const FIELD = 'value';

const messages = defineMessages({
  duplicate: {
    id: 'ordered-list-duplicate',
    defaultMessage: '{value} is already on the list.',
  },
});

type Props = {
  id: string;
  title: string;
  value?: string[] | null;
  /** The list's value type, as `plone.restapi` serializes it. */
  items?: Record<string, any>;
  /** Whether the backend refuses the same entry twice. */
  uniqueItems?: boolean;
  onChange: (id: string, value: string[]) => void;
  [key: string]: unknown;
};

/**
 * The schema one entry is edited with.
 *
 * @param title The list field's title, used when the value type has none.
 * @param items The list's value type.
 * @returns A schema with a single required field carrying the value type.
 */
export function stringItemSchema(
  title: string,
  items: Record<string, any> = {},
): ItemSchema {
  const itemTitle = items.title || title;
  return {
    title: itemTitle,
    fieldsets: [{ id: 'default', title: 'Default', fields: [FIELD] }],
    properties: { [FIELD]: { ...items, title: itemTitle } },
    required: [FIELD],
  };
}

const OrderedStringListWidget: React.FC<Props> = (props) => {
  const { id, title, value, items, uniqueItems, onChange } = props;
  const intl = useIntl();
  const schema = useMemo(() => stringItemSchema(title, items), [title, items]);
  const entries = value ?? [];

  const validate = (row: Row, index: number | null) => {
    const candidate = row[FIELD];
    const taken = entries.some(
      (entry, position) => position !== index && entry === candidate,
    );
    return taken
      ? intl.formatMessage(messages.duplicate, { value: String(candidate) })
      : undefined;
  };

  return (
    <OrderedListTable
      {...props}
      rows={entries.map((entry) => ({ [FIELD]: entry }))}
      schema={schema}
      columns={[FIELD]}
      onChangeRows={(rows) =>
        onChange(
          id,
          rows.map((row) => String(row[FIELD])),
        )
      }
      validate={uniqueItems ? validate : undefined}
    />
  );
};

export default OrderedStringListWidget;
