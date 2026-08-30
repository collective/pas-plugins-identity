/**
 * The provider form, composed from what the backend already sent.
 *
 * This file used to *build* the schema: 529 lines turning a hand-written
 * descriptor dict — `{type, title, required, secret, order}` — into Volto
 * properties, with its own notion of field types, its own ordering by a
 * spaced-out `order` key, its own secret flag, and its own untranslated
 * English strings. Érico's verdict (2026-08-29) was that it made a Classic UI
 * form impossible and reinvented, worse, what Plone already had.
 *
 * So the backend now serves two ordinary JSON schemas, produced by
 * `plone.restapi` from two interfaces:
 *
 * - `@identity-providers` sends the provider's own fields, from
 *   `IProviderRecords` — the same interface its registry records are bound
 *   to, so the form and the storage cannot describe different things.
 * - `@identity-drivers` sends each driver's settings, from its
 *   `settings_schema`.
 *
 * What is left here is composition, and only composition: merge the two,
 * prefix the driver's half so a flat form can carry a nested object, and add
 * the two fields that exist only while a provider is being created. Nothing
 * below decides what a field looks like — that is the backend's answer, in
 * the site's language, and this file must never start having an opinion about
 * it again.
 * @module helpers/providerSchema
 */
import { defineMessages } from 'react-intl';

import { toGroupRows, fromGroupRows } from './groupmap';
import { toRows, fromRows } from './propertymap';
import type { Driver, JsonSchema, VoltoSchema } from '../types';

import type { IntlShape } from 'react-intl';

/**
 * Prefix a driver setting carries in form data.
 *
 * The API nests them under `config`, and a Volto form is flat. The prefix is
 * what lets one flat object round-trip both halves without the two colliding
 * — a driver may perfectly well declare a `title`, and it is not the
 * provider's.
 */
export const CONFIG_PREFIX = 'config.';

/** Fieldset the driver's own settings are rendered in. */
export const SETTINGS_FIELDSET = 'settings';

/** Fieldset the two claim mappings are rendered in. */
export const MAPPING_FIELDSET = 'mapping';

/**
 * Fields `IProviderRecords` declares that this file renders itself.
 *
 * The served schema describes a provider's *storage*, which is right, and
 * three of its fields are not renderable as described. `driver` is a picker
 * over the registered drivers and is asked only while adding -- a provider's
 * driver is not an editable property, and the served `TextLine` would win,
 * because the merge below arrives after the picker is put in. `propertymap`
 * and `groupmap` are `Dict` fields, which Volto has no widget for at all;
 * they are rebuilt as row editors in a fieldset of their own. So the served
 * descriptions of the three are dropped rather than merged.
 */
const COMPOSED_HERE = ['driver', 'propertymap', 'groupmap'];

const messages = defineMessages({
  identity: { id: 'Identity', defaultMessage: 'Identity' },
  driver: { id: 'Driver', defaultMessage: 'Driver' },
  driverHelp: {
    id: 'provider-driver-help',
    defaultMessage:
      'Which service this provider talks to. It decides the rest of the ' +
      'form, and it cannot be changed afterwards.',
  },
  providerId: { id: 'Provider id', defaultMessage: 'Provider id' },
  providerIdHelp: {
    id: 'provider-id-help',
    defaultMessage:
      'Used in URLs and stored with every identity linked through this ' +
      'provider, so it is permanent.',
  },
  settings: { id: 'Settings', defaultMessage: 'Settings' },
  mapping: { id: 'Mapping', defaultMessage: 'Mapping' },
  propertymap: { id: 'Property map', defaultMessage: 'Property map' },
  groupmap: { id: 'Group map', defaultMessage: 'Group map' },
});

/**
 * Suggest an id for a provider being added.
 *
 * Slugified from the driver's title, which reads better than its id for the
 * one thing that becomes permanent the moment it is saved. Unchanged by the
 * schema rewrite: it is about naming a provider, not about describing a
 * field.
 *
 * @param drivers Every registered driver.
 * @param driverId The driver just chosen.
 * @returns A suggested id, or an empty string.
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
 * Build the provider form from the two schemas the backend sent.
 *
 * @param served The provider's own schema, from `@identity-providers`.
 * @param drivers Every registered driver, each carrying its settings schema.
 * @param driverId The driver whose settings to render.
 * @param adding Whether this is the add form, which asks two more questions.
 * @param intl For the labels of the fields that exist only in this form.
 * @returns A Volto schema.
 */
export function providerSchema(
  served: JsonSchema | undefined,
  drivers: Driver[],
  driverId: string | undefined,
  adding: boolean,
  intl: IntlShape,
): VoltoSchema {
  const properties: Record<string, Record<string, unknown>> = {};
  const fieldsets: { id: string; title: string; fields: string[] }[] = [];
  const required: string[] = (served?.required ?? []).filter(
    (name) => !COMPOSED_HERE.includes(name),
  );

  if (adding) {
    // The only two fields this file still invents, and they are not stored
    // anywhere: the driver decides which schema the rest of the form uses,
    // and the id becomes the record prefix. Both are answered once, at
    // creation, and neither exists on a provider that already exists.
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
    required.push('driver', 'id');
  }

  Object.assign(
    properties,
    Object.fromEntries(
      Object.entries(served?.properties ?? {}).filter(
        ([name]) => !COMPOSED_HERE.includes(name),
      ),
    ),
  );

  // The backend's own fieldsets, in its order, with the creation questions
  // folded into the first one so they are the first thing asked.
  (served?.fieldsets ?? []).forEach((fieldset, index) => {
    const extra = adding && index === 0 ? ['driver', 'id'] : [];
    const fields = [
      ...extra,
      ...fieldset.fields.filter((name) => !COMPOSED_HERE.includes(name)),
    ];
    // A fieldset the filter empties is not rendered as an empty tab.
    if (!fields.length) return;
    fieldsets.push({
      id: fieldset.id,
      title:
        index === 0 ? intl.formatMessage(messages.identity) : fieldset.title,
      fields,
    });
  });

  const driver = drivers.find((d) => d.id === driverId);
  const settings: JsonSchema = driver?.schema ?? {};
  const settingFields: string[] = [];
  for (const [name, property] of Object.entries(settings.properties ?? {})) {
    const key = `${CONFIG_PREFIX}${name}`;
    properties[key] = property;
    settingFields.push(key);
    if ((settings.required ?? []).includes(name)) {
      required.push(key);
    }
  }
  if (settingFields.length) {
    fieldsets.push({
      id: SETTINGS_FIELDSET,
      title: intl.formatMessage(messages.settings),
      // The driver's own fieldset order, flattened: a provider form shows one
      // Settings tab rather than repeating the driver's internal grouping
      // beside the provider's.
      fields: (settings.fieldsets ?? []).length
        ? (settings.fieldsets ?? []).flatMap((f) =>
            f.fields.map((name) => `${CONFIG_PREFIX}${name}`),
          )
        : settingFields,
    });
  }

  // The two mappings. Their *shape* is `Dict` on the backend; Volto has no
  // Dict widget, so they are edited as rows and converted below. That is a
  // widget gap rather than a schema this file invented.
  properties.propertymap = {
    title: intl.formatMessage(messages.propertymap),
    widget: 'object_list',
    schema: rowSchema(intl, 'claim', 'field'),
  };
  // The group map, only for a driver whose providers have groups. The
  // backend declares that by putting a `group_claim` field in the settings
  // schema, and it is the same switch on both ends: a driver with no groups
  // offers no claim to read them from, and a map stored against one grants
  // nothing. Asking an operator to map the groups of a magic link would be
  // asking a question with no answer.
  const hasGroups = Boolean(settings.properties?.group_claim);
  if (hasGroups) {
    properties.groupmap = {
      title: intl.formatMessage(messages.groupmap),
      widget: 'object_list',
      schema: rowSchema(intl, 'group', 'local'),
    };
  }
  fieldsets.push({
    id: MAPPING_FIELDSET,
    title: intl.formatMessage(messages.mapping),
    fields: hasGroups ? ['propertymap', 'groupmap'] : ['propertymap'],
  });

  return { fieldsets, properties, required };
}

/**
 * The two-column schema a mapping row is edited with.
 *
 * @param intl For the column labels.
 * @param left Name of the left-hand field.
 * @param right Name of the right-hand field.
 * @returns A Volto schema for one row.
 */
function rowSchema(intl: IntlShape, left: string, right: string): VoltoSchema {
  return {
    fieldsets: [{ id: 'default', title: 'default', fields: [left, right] }],
    properties: {
      [left]: { title: left, type: 'string' },
      [right]: { title: right, type: 'string' },
    },
    required: [],
  };
}

/**
 * Turn a provider from the API into form data.
 *
 * @param provider The provider, or undefined when adding.
 * @param defaults Seeds for a provider being added.
 * @returns Flat form data.
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
      show_in_login: true,
      propertymap: toRows(defaults?.propertymap),
      groupmap: toGroupRows(defaults?.groupmap),
    };
  }
  const data: Record<string, unknown> = {
    title: provider.title ?? '',
    enabled: provider.enabled ?? true,
    // Absent means shown. A provider stored before the setting existed was
    // on the login page, and reading the key back as false would take a
    // site's login buttons away on upgrade.
    show_in_login: provider.show_in_login ?? true,
    // The upload envelope the backend sends, handed to the widget unchanged.
    icon: provider.icon ?? '',
    background_color: provider.background_color ?? '',
    foreground_color: provider.foreground_color ?? '',
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
 * Only shape, never validation. Every rule about what a value may be lives on
 * the backend schema now — a colour it cannot parse, an icon that is not SVG,
 * a redirect URI a browser could execute — so trimming here would only hide
 * which value the refusal is about.
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
  payload.enabled = Boolean(payload.enabled);
  payload.show_in_login = Boolean(payload.show_in_login);
  if (typeof payload.id === 'string') {
    payload.id = payload.id.trim();
  }
  return payload;
}
