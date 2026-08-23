/**
 * The claim-to-user-field mapping editor.
 *
 * Built on Volto's `ObjectListWidget`, which is its DataGridField
 * equivalent: a list of rows edited against a schema. That gives drag
 * reordering, add and remove, and -- the reason it is worth using here --
 * schema-driven widgets for the columns, so the user field renders as a
 * vocabulary-backed select without this package fetching anything itself.
 * @module components/ControlPanel/PropertyMapField
 */
import React, { useMemo } from 'react';
import ObjectListWidget from '@plone/volto/components/manage/Widgets/ObjectListWidget';

import { USER_FIELDS_VOCABULARY } from '../../constants/vocabularies';
import type { PropertyMapRow } from '../../helpers/propertymap';

/** One column of the mapping editor, as Volto's form machinery reads it. */
interface SchemaProperty {
  title: string;
  description?: string;
  type?: string;
  /** Present only on a column whose values come from the backend. */
  vocabulary?: { '@id': string };
}

/** The schema one mapping row is edited against. */
interface RowSchema {
  title: string;
  fieldsets: { id: string; title: string; fields: string[] }[];
  properties: Record<string, SchemaProperty>;
  required: string[];
}

interface PropertyMapFieldProps {
  id: string;
  /**
   * The rows, held by the panel rather than derived here. A row the
   * operator has just added is not yet a mapping, so it would vanish the
   * moment it round-tripped through the stored map.
   */
  rows: PropertyMapRow[];
  disabled?: boolean;
  onChange: (rows: PropertyMapRow[]) => void;
}

/**
 * Build the schema for one mapping row.
 *
 * @returns A Volto schema with a free-text claim and a vocabulary-backed
 *   user field.
 */
export function rowSchema(): RowSchema {
  return {
    title: 'Mapping',
    fieldsets: [
      { id: 'default', title: 'Default', fields: ['claim', 'field'] },
    ],
    properties: {
      claim: {
        title: 'Provider claim',
        description:
          'Dotted path into the claims, for example email or ' +
          'address.formatted. Normalized claims are tried before the ' +
          "provider's raw payload.",
        type: 'string',
      },
      field: {
        title: 'User field',
        description: "Where the value is written on the user's profile.",
        // The site's own member schema, so a field added in the User Schema
        // control panel appears here without a frontend change.
        vocabulary: { '@id': USER_FIELDS_VOCABULARY },
      },
    },
    required: ['claim', 'field'],
  };
}

const PropertyMapField: React.FC<PropertyMapFieldProps> = ({
  id,
  rows,
  disabled = false,
  onChange,
}) => {
  const schema = useMemo(() => rowSchema(), []);

  return (
    <div className="identity-propertymap" data-disabled={disabled || undefined}>
      <ObjectListWidget
        id={id}
        title="Attribute mapping"
        description="What each provider claim writes onto the Plone user. A field that already has a value locally is left alone."
        schema={schema}
        value={rows}
        onChange={(_name: string, next: PropertyMapRow[]) => onChange(next)}
      />
    </div>
  );
};

export default PropertyMapField;
