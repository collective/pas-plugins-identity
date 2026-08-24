/**
 * Build the Volto form schema for a provider.
 *
 * Nothing here enumerates a provider's fields. The driver describes its own
 * configuration over ``@identity-drivers`` -- name, title, description,
 * type and whether it is secret -- and this turns that into the schema
 * Volto's `Form` renders. Adding a driver on the backend therefore adds its
 * form here with no frontend change.
 * @module helpers/providerSchema
 */
import { USER_FIELDS_VOCABULARY } from '../constants/vocabularies';
import type { Driver, DriverField } from '../types';

/** A Volto form schema, as `Form` consumes it. */
export interface VoltoSchema {
  title: string;
  fieldsets: { id: string; title: string; fields: string[] }[];
  properties: Record<string, Record<string, unknown>>;
  required: string[];
}

/** Prefix that keeps a driver's fields out of the provider's own namespace. */
export const CONFIG_PREFIX = 'config.';

/**
 * Turn one driver field descriptor into a Volto schema property.
 *
 * @param field The descriptor from the driver.
 * @returns The schema property.
 */
export function propertyFor(field: DriverField): Record<string, unknown> {
  const base = {
    title: field.title,
    description: field.description,
    // The driver's own default. Without it an add form starts blank and the
    // operator has to know what a sensible value is -- which is how a GitHub
    // provider ends up with OIDC scopes typed into it and never sees an
    // email address.
    ...(field.default === undefined ? {} : { default: field.default }),
  };
  if (field.secret) {
    // Volto's password widget, so a stored secret is not shoulder-readable
    // and the browser does not offer to remember it.
    return { ...base, widget: 'password' };
  }
  if (field.type === 'int') {
    return { ...base, type: 'number' };
  }
  if (field.type === 'bool') {
    return { ...base, type: 'boolean' };
  }
  if (field.type === 'list') {
    // A repeating value, not a comma-separated string in a text box.
    return { ...base, type: 'array', widget: 'token' };
  }
  if (field.type === 'choice') {
    // The driver names the options, so a select renders whatever a driver
    // offers without this knowing what any of them mean.
    return { ...base, choices: field.choices ?? [] };
  }
  return { ...base, type: 'string' };
}

/** The mapping rows, edited with Volto's DataGridField equivalent. */
function propertymapProperty(): Record<string, unknown> {
  return {
    title: 'Attribute mapping',
    description:
      'What each provider claim writes onto the Plone user. A field that ' +
      'already has a value locally is left alone.',
    widget: 'object_list',
    schema: {
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
          vocabulary: { '@id': USER_FIELDS_VOCABULARY },
        },
      },
      required: ['claim', 'field'],
    },
  };
}

/**
 * Build the schema for adding or editing a provider.
 *
 * @param drivers Every registered driver, for the driver choice.
 * @param driverId The driver whose fields should be rendered, if one is
 *   chosen yet.
 * @param adding Whether this is the add form, which also asks for an id and
 *   lets the driver be chosen.
 * @returns The schema.
 */
export function providerSchema(
  drivers: Driver[],
  driverId: string | undefined,
  adding: boolean,
): VoltoSchema {
  const driver = drivers.find((d) => d.id === driverId);
  const properties: Record<string, Record<string, unknown>> = {};
  const identity: string[] = [];

  if (adding) {
    properties.id = {
      title: 'Provider ID',
      description:
        'Permanent. It is stored on every identity linked through this ' +
        'provider, so renaming it later would orphan them all. Letters, ' +
        'digits, - and _ only.',
      type: 'string',
    };
    properties.driver = {
      title: 'Driver',
      description: 'Which integration handles this provider.',
      choices: drivers.map((d) => [d.id, d.title]),
    };
    identity.push('id', 'driver');
  }

  properties.title = {
    title: 'Title',
    description: 'What the sign-in button says. Defaults to the driver name.',
    type: 'string',
  };
  properties.enabled = {
    title: 'Enabled',
    description: 'A disabled provider is configured but offered to nobody.',
    type: 'boolean',
  };
  identity.push('title', 'enabled');

  const settings = Object.entries(driver?.schema ?? {}).map(([name, field]) => {
    const key = `${CONFIG_PREFIX}${name}`;
    properties[key] = propertyFor(field);
    return key;
  });

  properties.propertymap = propertymapProperty();

  const fieldsets = [
    { id: 'default', title: 'Provider', fields: identity },
    // Only once a driver is chosen: before that there is no honest set of
    // fields to show, and an empty fieldset reads as a broken form.
    ...(settings.length
      ? [
          {
            id: 'settings',
            title: driver?.title ?? 'Settings',
            fields: settings,
          },
        ]
      : []),
    { id: 'mapping', title: 'Attribute mapping', fields: ['propertymap'] },
  ];

  const required = Object.entries(driver?.schema ?? {})
    .filter(([, field]) => field.required)
    .map(([name]) => `${CONFIG_PREFIX}${name}`);

  return {
    title: adding ? 'Add a provider' : 'Edit provider',
    fieldsets,
    properties,
    required: adding ? ['id', 'driver', ...required] : required,
  };
}

/**
 * Seed a form from a stored provider.
 *
 * Config values are flattened onto prefixed keys because a Volto schema is
 * flat; the mapping becomes rows because that is what the list widget edits.
 *
 * @param provider The provider being edited, or undefined when adding.
 * @param toRows Converter for the stored mapping.
 * @returns Form data.
 */
export function toFormData(
  provider: Record<string, any> | undefined,
  toRows: (map: Record<string, string> | undefined) => unknown[],
): Record<string, unknown> {
  if (!provider) {
    return { enabled: true, propertymap: [] };
  }
  const data: Record<string, unknown> = {
    title: provider.title ?? '',
    enabled: provider.enabled ?? true,
    propertymap: toRows(provider.propertymap),
  };
  for (const [name, value] of Object.entries(provider.config ?? {})) {
    data[`${CONFIG_PREFIX}${name}`] = value;
  }
  return data;
}

/**
 * Turn submitted form data back into the API payload.
 *
 * @param formData What the form submitted.
 * @param fromRows Converter for the mapping rows.
 * @returns The body for POST or PATCH.
 */
export function fromFormData(
  formData: Record<string, any>,
  fromRows: (rows: any) => Record<string, string>,
): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const payload: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(formData ?? {})) {
    if (key.startsWith(CONFIG_PREFIX)) {
      config[key.slice(CONFIG_PREFIX.length)] = value;
    } else if (key === 'propertymap') {
      payload.propertymap = fromRows(value);
    } else if (!key.startsWith('@')) {
      payload[key] = value;
    }
  }

  payload.config = config;
  payload.title = String(payload.title ?? '').trim();
  payload.enabled = Boolean(payload.enabled);
  if (typeof payload.id === 'string') {
    payload.id = payload.id.trim();
  }
  return payload;
}
