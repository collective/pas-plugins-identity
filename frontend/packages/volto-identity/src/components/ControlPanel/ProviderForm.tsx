/**
 * A provider's configuration form, generated from its driver's schema.
 *
 * Nothing here knows what a "client secret" is: the driver says which fields
 * exist and which are secret, and this renders that (§4.5). Adding a driver
 * on the backend therefore adds its form here with no frontend change.
 * @module components/ControlPanel/ProviderForm
 */
import React from 'react';
import type { Driver, DriverField } from '../../types';

interface ProviderFormProps {
  driver: Driver;
  values: Record<string, unknown>;
  disabled?: boolean;
  onChange: (name: string, value: unknown) => void;
}

/** What the backend sends in place of a stored secret. */
export const SECRET_SENTINEL = '••••••••';

/**
 * Pick the input type for a schema field.
 *
 * @param field The field descriptor.
 * @returns An HTML input type.
 */
export function inputType(field: DriverField): string {
  if (field.secret) {
    return 'password';
  }
  if (field.type === 'int') {
    return 'number';
  }
  return 'text';
}

const ProviderForm: React.FC<ProviderFormProps> = ({
  driver,
  values,
  disabled = false,
  onChange,
}) => (
  <fieldset className="identity-provider-form" disabled={disabled}>
    <legend>{driver.title}</legend>
    {Object.entries(driver.schema).map(([name, field]) => {
      const id = `identity-field-${driver.id}-${name}`;
      const value = values[name];

      if (field.type === 'bool') {
        return (
          <div key={name} className="identity-field">
            <input
              id={id}
              name={name}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(event) => onChange(name, event.target.checked)}
            />
            <label htmlFor={id}>{field.title}</label>
            {field.description ? <p>{field.description}</p> : null}
          </div>
        );
      }

      return (
        <div key={name} className="identity-field">
          <label htmlFor={id}>{field.title}</label>
          <input
            id={id}
            name={name}
            type={inputType(field)}
            required={Boolean(field.required)}
            value={value === undefined || value === null ? '' : String(value)}
            // A stored secret arrives masked. Leaving it exactly as it came
            // back is what tells the backend to keep it (S7/I4), so the field
            // is editable but never pre-filled with anything real.
            placeholder={field.secret ? SECRET_SENTINEL : undefined}
            onChange={(event) => onChange(name, event.target.value)}
          />
          {field.description ? <p>{field.description}</p> : null}
        </div>
      );
    })}
  </fieldset>
);

export default ProviderForm;
