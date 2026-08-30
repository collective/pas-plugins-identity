/**
 * The provider form is composed, not invented.
 *
 * This file used to be 618 lines, and most of them asserted things about a
 * schema language this package had made up: that a `secret` descriptor became
 * a password widget, that `order` sorted the fields, that a `choice` became a
 * select. None of that is decided here any more — the backend serializes two
 * interfaces with `plone.restapi` and this helper merges them — so what is
 * left to test is the merge, and the one thing the merge must never do, which
 * is have an opinion about a field.
 */
import { describe, expect, it } from 'vitest';

import {
  CONFIG_PREFIX,
  MAPPING_FIELDSET,
  SETTINGS_FIELDSET,
  fromFormData,
  providerSchema,
  suggestedProviderId,
  toFormData,
} from './providerSchema';
import type { Driver } from '../types';

const intl = {
  formatMessage: (m: { defaultMessage: string }) => m.defaultMessage,
} as any;

/** What `@identity-providers` sends: `IProviderRecords`, serialized. */
const SERVED = {
  type: 'object',
  properties: {
    title: { title: 'Title', type: 'string' },
    enabled: { title: 'Enabled', type: 'boolean' },
    icon: { title: 'Icon', type: 'string', widget: 'provider_icon' },
    background_color: { title: 'Background colour', widget: 'color_picker' },
  },
  required: ['title'],
  fieldsets: [
    { id: 'default', title: 'Default', fields: ['title', 'enabled'] },
    { id: 'style', title: 'Style', fields: ['icon', 'background_color'] },
  ],
};

/** What one entry of `@identity-drivers` sends: the driver's settings. */
const GITHUB: Driver = {
  id: 'github',
  title: 'GitHub',
  schema: {
    properties: {
      client_id: { title: 'Client ID', type: 'string' },
      client_secret: { title: 'Client secret', widget: 'password' },
    },
    required: ['client_id', 'client_secret'],
    fieldsets: [
      {
        id: 'default',
        title: 'Default',
        fields: ['client_id', 'client_secret'],
      },
    ],
  },
} as Driver;

const DRIVERS = [GITHUB];

describe('providerSchema', () => {
  it('carries the served properties through untouched', () => {
    // The point of the whole change: whatever the backend decided about a
    // field — its widget, its title, its type — arrives unaltered.
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(schema.properties.icon).toEqual(SERVED.properties.icon);
    expect(schema.properties.background_color).toEqual(
      SERVED.properties.background_color,
    );
  });

  it('keeps the backend fieldsets and their order', () => {
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual([
      'default',
      'style',
      SETTINGS_FIELDSET,
      MAPPING_FIELDSET,
    ]);
  });

  it('prefixes the driver settings so the two halves cannot collide', () => {
    // A driver may perfectly well declare a `title`, and it is not the
    // provider's.
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(schema.properties[`${CONFIG_PREFIX}client_id`]).toEqual({
      title: 'Client ID',
      type: 'string',
    });
    expect(schema.properties.title).toEqual(SERVED.properties.title);
  });

  it('carries required through from both halves', () => {
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(schema.required).toContain('title');
    expect(schema.required).toContain(`${CONFIG_PREFIX}client_secret`);
  });

  it('renders the driver settings in the order the driver declared', () => {
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);
    const settings = schema.fieldsets.find((f) => f.id === SETTINGS_FIELDSET);

    expect(settings?.fields).toEqual([
      `${CONFIG_PREFIX}client_id`,
      `${CONFIG_PREFIX}client_secret`,
    ]);
  });

  it('asks for the driver and the id only while adding', () => {
    const adding = providerSchema(SERVED, DRIVERS, 'github', true, intl);
    const editing = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(adding.fieldsets[0].fields.slice(0, 2)).toEqual(['driver', 'id']);
    expect(editing.properties.driver).toBeUndefined();
    expect(editing.properties.id).toBeUndefined();
  });

  it('survives a backend that sent no schema', () => {
    // A client talking to an older backend, or a request that failed. An
    // empty form is recoverable; a crash on `schema.fieldsets` is not.
    const schema = providerSchema(undefined, DRIVERS, 'github', false, intl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual([
      SETTINGS_FIELDSET,
      MAPPING_FIELDSET,
    ]);
  });

  it('survives a driver that is not registered', () => {
    const schema = providerSchema(SERVED, DRIVERS, 'gone', false, intl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual([
      'default',
      'style',
      MAPPING_FIELDSET,
    ]);
  });
});

describe('suggestedProviderId', () => {
  it('slugifies the driver title', () => {
    expect(suggestedProviderId(DRIVERS, 'github')).toBe('github');
  });

  it('turns punctuation into separators rather than dropping it', () => {
    const drivers = [{ id: 'x', title: 'Sign in (beta)' } as Driver];

    expect(suggestedProviderId(drivers, 'x')).toBe('sign-in-beta');
  });

  it('is empty for a driver that is not there', () => {
    expect(suggestedProviderId(DRIVERS, 'nope')).toBe('');
  });
});

describe('toFormData', () => {
  it('flattens the driver settings under the prefix', () => {
    const data = toFormData({
      title: 'GitHub',
      config: { client_id: 'abc' },
    });

    expect(data[`${CONFIG_PREFIX}client_id`]).toBe('abc');
  });

  it('reads an absent show_in_login as shown', () => {
    // A provider stored before the setting existed was on the login page, and
    // reading the key back as false would take a site's buttons away.
    expect(toFormData({ title: 'x' }).show_in_login).toBe(true);
  });

  it('hands the icon envelope to the widget unchanged', () => {
    const envelope = 'filenameb64:aWNvbi5zdmc=;datab64:PHN2Zy8+';

    expect(toFormData({ icon: envelope }).icon).toBe(envelope);
  });
});

describe('fromFormData', () => {
  it('nests the prefixed settings back under config', () => {
    const payload = fromFormData({
      title: 'GitHub',
      [`${CONFIG_PREFIX}client_id`]: 'abc',
    });

    expect(payload.config).toEqual({ client_id: 'abc' });
    expect(payload.title).toBe('GitHub');
  });

  it('drops the keys Volto adds to its own form data', () => {
    const payload = fromFormData({ '@id': '/x', title: 'GitHub' });

    expect(payload['@id']).toBeUndefined();
  });

  it('does not validate anything', () => {
    // Every rule about what a value may be lives on the backend schema now.
    // Trimming or correcting here would only hide which value a refusal is
    // about.
    const payload = fromFormData({ background_color: '  not a colour  ' });

    expect(payload.background_color).toBe('  not a colour  ');
  });
});
