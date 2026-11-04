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
 * is one -- refuses an entry already on it, compared the way the backend
 * compares: trimmed, and for an `Email` without regard to case, since the
 * backend stores every address lowercased.
 *
 * An entry is stored trimmed, and an empty one is not stored at all.
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
 * Whether the list's value type is an email address.
 *
 * @param items The list's value type, as `plone.restapi` serializes it.
 * @returns True for a `schema.Email` value type.
 */
export function isEmailType(items: Record<string, any> = {}): boolean {
  return items.widget === 'email' || items.factory === 'Email';
}

/**
 * The form an entry is compared in, to find a duplicate.
 *
 * @param entry The entry.
 * @param email Whether entries are email addresses.
 * @returns The entry trimmed, and lowercased for an address.
 */
export function comparable(entry: unknown, email: boolean): string {
  const text = String(entry ?? '').trim();
  return email ? text.toLowerCase() : text;
}

/**
 * The value to store from the table's entries.
 *
 * @param rows The entries, as the table edits them.
 * @returns Each entry's text, trimmed, with empty ones left out.
 */
export function storedValues(rows: Row[]): string[] {
  return rows
    .map((row) => String(row[FIELD] ?? '').trim())
    .filter((entry) => entry !== '');
}

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

  const email = isEmailType(items);

  const validate = (row: Row, index: number | null) => {
    const candidate = comparable(row[FIELD], email);
    const taken = entries.some(
      (entry, position) =>
        position !== index && comparable(entry, email) === candidate,
    );
    return taken
      ? intl.formatMessage(messages.duplicate, {
          value: String(row[FIELD] ?? '').trim(),
        })
      : undefined;
  };

  return (
    <OrderedListTable
      {...props}
      rows={entries.map((entry) => ({ [FIELD]: entry }))}
      schema={schema}
      columns={[FIELD]}
      onChangeRows={(rows) => onChange(id, storedValues(rows))}
      validate={uniqueItems ? validate : undefined}
    />
  );
};

export default OrderedStringListWidget;
