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
import {
  GROUPS_VOCABULARY,
  USER_FIELDS_VOCABULARY,
} from '../constants/vocabularies';
import { fromGroupRows, toGroupRows } from './groupmap';
import { fromRows, toRows } from './propertymap';
import type { Driver, DriverField } from '../types';
import { defineMessages } from 'react-intl';
import type { IntlShape } from 'react-intl';

/**
 * Every label this module writes itself.
 *
 * A driver's *own* fields are not here: their titles and descriptions arrive
 * from the backend over `@identity-drivers`, as plain strings rather than
 * message ids, so they are rendered as sent. See `propertyFor`.
 */
const messages = defineMessages({
  driver: { id: 'Driver', defaultMessage: 'Driver' },
  driverHelp: {
    id: 'Which integration handles this provider.',
    defaultMessage: 'Which integration handles this provider.',
  },
  providerId: { id: 'Provider ID', defaultMessage: 'Provider ID' },
  providerIdHelp: {
    id: 'provider-id-help',
    defaultMessage:
      'Permanent. It is stored on every identity linked through this ' +
      'provider, so renaming it later would orphan them all. Letters, ' +
      'digits, - and _ only.',
  },
  title: { id: 'Title', defaultMessage: 'Title' },
  titleHelp: {
    id: 'provider-title-help',
    defaultMessage:
      'What the sign-in button says. Defaults to the driver name.',
  },
  enabled: { id: 'Enabled', defaultMessage: 'Enabled' },
  enabledHelp: {
    id: 'provider-enabled-help',
    defaultMessage: 'A disabled provider is configured but offered to nobody.',
  },
  settings: { id: 'Settings', defaultMessage: 'Settings' },
  provider: { id: 'Provider', defaultMessage: 'Provider' },
  mapping: { id: 'Mapping', defaultMessage: 'Mapping' },
  addProvider: { id: 'Add a provider', defaultMessage: 'Add a provider' },
  editProvider: { id: 'Edit provider', defaultMessage: 'Edit provider' },
  attributeMapping: {
    id: 'Attribute mapping',
    defaultMessage: 'Attribute mapping',
  },
  attributeMappingHelp: {
    id: 'attribute-mapping-help',
    defaultMessage:
      'What each provider claim writes onto the Plone user. A field that ' +
      'already has a value locally is left alone.',
  },
  providerClaim: { id: 'Provider claim', defaultMessage: 'Provider claim' },
  providerClaimHelp: {
    id: 'provider-claim-help',
    defaultMessage:
      'Dotted path into the claims, for example email or address.formatted. ' +
      "Normalized claims are tried before the provider's raw payload.",
  },
  userField: { id: 'User field', defaultMessage: 'User field' },
  userFieldHelp: {
    id: 'user-field-help',
    defaultMessage: "Where the value is written on the user's profile.",
  },
  groupMapping: { id: 'Group mapping', defaultMessage: 'Group mapping' },
  groupMappingHelp: {
    id: 'group-mapping-help',
    defaultMessage:
      "Which of the provider's groups grant a group here. Empty grants " +
      'nothing. Every sign-in reconciles, so a membership revoked at the ' +
      'provider stops granting here -- but only groups this provider ' +
      'granted are ever taken back, so a group you granted by hand is safe.',
  },
  providerGroup: { id: 'Provider group', defaultMessage: 'Provider group' },
  providerGroupHelp: {
    id: 'provider-group-help',
    defaultMessage:
      "The group's name as the provider sends it. Free text: this site " +
      'cannot enumerate the far end. A name with no row here grants ' +
      'nothing, and is never created.',
  },
  localGroup: { id: 'Local group', defaultMessage: 'Local group' },
  localGroupHelp: {
    id: 'local-group-help',
    defaultMessage:
      'The group it grants on this site. A group that does not exist here ' +
      'grants nothing.',
  },
});

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
 * A driver's fields, in the order the driver wants them rendered.
 *
 * `@identity-drivers` answers with a JSON object, and plone.restapi
 * serialises those with `sort_keys=True` -- so what arrives here is
 * alphabetical whatever the driver declared, which puts `auto_link_by_email`
 * above `client_id`. Each descriptor carries its own position instead.
 *
 * @param schema The driver's schema.
 * @returns The entries, sorted; ties and missing positions fall back to the
 *   field name, so the result is stable rather than merely sorted.
 */
export function orderedFields(
  schema: Record<string, DriverField>,
): [string, DriverField][] {
  return Object.entries(schema).sort(
    ([nameA, a], [nameB, b]) =>
      (a.order ?? Number.MAX_SAFE_INTEGER) -
        (b.order ?? Number.MAX_SAFE_INTEGER) || nameA.localeCompare(nameB),
  );
}

/**
 * Suggest a provider id for a driver.
 *
 * The id is permanent and stored on every identity linked through the
 * provider, so it is worth prefilling with something sane rather than
 * leaving an operator to invent one -- most sites have exactly one provider
 * per driver and want it called after the driver.
 *
 * @param drivers Every registered driver.
 * @param driverId The driver chosen, if one is chosen yet.
 * @returns The slugified driver title, or an empty string when no driver is
 *   chosen or its title slugifies to nothing.
 */
export function suggestedProviderId(
  drivers: Driver[],
  driverId: string | undefined,
): string {
  const driver = drivers.find((d) => d.id === driverId);
  if (!driver) {
    return '';
  }
  return (
    driver.title
      .toLowerCase()
      // The id accepts letters, digits, - and _ only, so everything else
      // becomes a separator rather than being dropped -- "Sign in (beta)"
      // should read as sign-in-beta, not signinbeta.
      .replace(/[^a-z0-9_]+/g, '-')
      .replace(/^-+|-+$/g, '') || driver.id
  );
}

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
function propertymapProperty(intl: IntlShape): Record<string, unknown> {
  return {
    title: intl.formatMessage(messages.attributeMapping),
    description: intl.formatMessage(messages.attributeMappingHelp),
    widget: 'object_list',
    schema: {
      title: intl.formatMessage(messages.mapping),
      fieldsets: [
        { id: 'default', title: 'Default', fields: ['claim', 'field'] },
      ],
      properties: {
        claim: {
          title: intl.formatMessage(messages.providerClaim),
          description: intl.formatMessage(messages.providerClaimHelp),
          type: 'string',
        },
        field: {
          title: intl.formatMessage(messages.userField),
          description: intl.formatMessage(messages.userFieldHelp),
          vocabulary: { '@id': USER_FIELDS_VOCABULARY },
        },
      },
      required: ['claim', 'field'],
    },
  };
}

/** The group mapping rows. */
function groupmapProperty(intl: IntlShape): Record<string, unknown> {
  return {
    title: intl.formatMessage(messages.groupMapping),
    description: intl.formatMessage(messages.groupMappingHelp),
    widget: 'object_list',
    schema: {
      title: intl.formatMessage(messages.mapping),
      fieldsets: [
        { id: 'default', title: 'Default', fields: ['group', 'local'] },
      ],
      properties: {
        group: {
          title: intl.formatMessage(messages.providerGroup),
          description: intl.formatMessage(messages.providerGroupHelp),
          type: 'string',
        },
        local: {
          title: intl.formatMessage(messages.localGroup),
          description: intl.formatMessage(messages.localGroupHelp),
          vocabulary: { '@id': GROUPS_VOCABULARY },
        },
      },
      required: ['group', 'local'],
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
  intl: IntlShape,
): VoltoSchema {
  const driver = drivers.find((d) => d.id === driverId);
  const properties: Record<string, Record<string, unknown>> = {};
  const identity: string[] = [];

  if (adding) {
    // Driver before id: it decides which fields the rest of the form even
    // has, so answering it first is the only order that reads forwards.
    properties.driver = {
      title: intl.formatMessage(messages.driver),
      description: intl.formatMessage(messages.driverHelp),
      choices: drivers.map((d) => [d.id, d.title]),
    };
    properties.id = {
      title: intl.formatMessage(messages.providerId),
      description: intl.formatMessage(messages.providerIdHelp),
      type: 'string',
    };
    identity.push('driver', 'id');
  }

  properties.title = {
    title: intl.formatMessage(messages.title),
    description: intl.formatMessage(messages.titleHelp),
    type: 'string',
  };
  properties.enabled = {
    title: intl.formatMessage(messages.enabled),
    description: intl.formatMessage(messages.enabledHelp),
    type: 'boolean',
  };
  identity.push('title', 'enabled');

  const settings = orderedFields(driver?.schema ?? {}).map(([name, field]) => {
    const key = `${CONFIG_PREFIX}${name}`;
    properties[key] = propertyFor(field);
    return key;
  });

  properties.propertymap = propertymapProperty(intl);

  // Only for a driver that says its providers have groups. The backend
  // declares that by putting a `group_claim` field in the schema, and it is
  // the same switch on both ends: a driver with no groups offers no claim to
  // read them from, and a map stored against one grants nothing. Asking an
  // operator to map the groups of a magic link would be asking a question
  // with no answer.
  const hasGroups = Boolean(driver?.schema?.group_claim);
  if (hasGroups) {
    properties.groupmap = groupmapProperty(intl);
  }

  const fieldsets = [
    {
      id: 'default',
      title: intl.formatMessage(messages.provider),
      fields: identity,
    },
    // Only once a driver is chosen: before that there is no honest set of
    // fields to show, and an empty fieldset reads as a broken form.
    ...(settings.length
      ? [
          {
            id: 'settings',
            title: driver?.title ?? intl.formatMessage(messages.settings),
            fields: settings,
          },
        ]
      : []),
    {
      id: 'mapping',
      title: intl.formatMessage(messages.mapping),
      fields: ['propertymap', ...(hasGroups ? ['groupmap'] : [])],
    },
  ];

  const required = Object.entries(driver?.schema ?? {})
    .filter(([, field]) => field.required)
    .map(([name]) => `${CONFIG_PREFIX}${name}`);

  return {
    title: intl.formatMessage(
      adding ? messages.addProvider : messages.editProvider,
    ),
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
 * @param defaults The chosen driver's seed mappings, used only when adding:
 *   an existing provider's own mappings are the whole truth about it,
 *   including the deliberate decision to have none.
 * @returns Form data.
 */
export function toFormData(
  provider: Record<string, any> | undefined,
  defaults?: {
    propertymap?: Record<string, string>;
    groupmap?: Record<string, string>;
  },
): Record<string, unknown> {
  if (!provider) {
    return {
      enabled: true,
      propertymap: toRows(defaults?.propertymap),
      groupmap: toGroupRows(defaults?.groupmap),
    };
  }
  const data: Record<string, unknown> = {
    title: provider.title ?? '',
    enabled: provider.enabled ?? true,
    propertymap: toRows(provider.propertymap),
    groupmap: toGroupRows(provider.groupmap),
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
 * @returns The body for POST or PATCH.
 */
export function fromFormData(
  formData: Record<string, any>,
): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const payload: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(formData ?? {})) {
    if (key.startsWith(CONFIG_PREFIX)) {
      config[key.slice(CONFIG_PREFIX.length)] = value;
    } else if (key === 'propertymap') {
      payload.propertymap = fromRows(value);
    } else if (key === 'groupmap') {
      payload.groupmap = fromGroupRows(value);
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
