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

/**
 * What `@identity-providers` sends: `IProviderRecords`, serialized.
 *
 * Including `driver`, `propertymap` and `groupmap`, which it really does
 * send -- they are fields of a provider's storage. Leaving them out of this
 * fixture is what let the merge below go unnoticed once already.
 */
const SERVED = {
  type: 'object',
  properties: {
    driver: { title: 'Driver', type: 'string' },
    title: { title: 'Title', type: 'string' },
    enabled: { title: 'Enabled', type: 'boolean' },
    propertymap: { title: 'Property map', type: 'object' },
    groupmap: { title: 'Group map', type: 'object' },
    icon: { title: 'Icon', type: 'string', widget: 'provider_icon' },
    background_color: { title: 'Background colour', widget: 'color_picker' },
  },
  required: ['title'],
  fieldsets: [
    {
      id: 'default',
      title: 'Default',
      fields: ['driver', 'title', 'enabled', 'propertymap', 'groupmap'],
    },
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

/** A driver whose providers have groups: the only difference that matters. */
const OIDC: Driver = {
  id: 'oidc',
  title: 'OpenID Connect',
  schema: {
    properties: {
      issuer: { title: 'Issuer URL', type: 'string' },
      group_claim: { title: 'Groups arrive in the claim', type: 'string' },
    },
    required: ['issuer'],
    fieldsets: [
      { id: 'default', title: 'Default', fields: ['issuer', 'group_claim'] },
    ],
  },
} as Driver;

const DRIVERS = [GITHUB, OIDC];

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

  it('renders the group map only for a driver that has groups', () => {
    // The backend says a driver's providers have groups by putting a
    // `group_claim` field in its settings schema, and this is the same
    // switch. GitHub declares none, so mapping them is a question with no
    // answer -- and a map stored against such a provider grants nothing.
    const withGroups = providerSchema(SERVED, DRIVERS, 'oidc', false, intl);
    const without = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(withGroups.properties.groupmap).toBeDefined();
    expect(
      withGroups.fieldsets.find((f) => f.id === MAPPING_FIELDSET)?.fields,
    ).toEqual(['propertymap', 'groupmap']);

    expect(without.properties.groupmap).toBeUndefined();
    expect(
      without.fieldsets.find((f) => f.id === MAPPING_FIELDSET)?.fields,
    ).toEqual(['propertymap']);
  });

  it('drops the served driver field rather than merging it', () => {
    // `IProviderRecords` has a `driver` TextLine, because storage does. The
    // form asks the question with a picker over the registered drivers, and
    // only while adding -- so the served description of it must not arrive
    // last and overwrite that.
    const adding = providerSchema(SERVED, DRIVERS, 'github', true, intl);

    expect(adding.properties.driver?.choices).toEqual([
      ['github', 'GitHub'],
      ['oidc', 'OpenID Connect'],
    ]);
    expect(adding.properties.driver?.type).toBeUndefined();
  });

  it('never lists a mapping twice', () => {
    // The served default fieldset carries `propertymap` and `groupmap`, and
    // this file rebuilds both as row editors in a fieldset of its own. A
    // field named in two fieldsets is rendered in both, once as a `Dict`
    // that Volto has no widget for.
    const schema = providerSchema(SERVED, DRIVERS, 'oidc', false, intl);
    const listed = schema.fieldsets.flatMap((f) => f.fields);

    expect(listed.filter((name) => name === 'propertymap')).toHaveLength(1);
    expect(listed.filter((name) => name === 'groupmap')).toHaveLength(1);
    expect(schema.fieldsets.find((f) => f.id === 'default')?.fields).toEqual([
      'title',
      'enabled',
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

describe('providerSchema and the driver fieldsets', () => {
  // A driver that groups its settings the way the shipped OIDC one does.
  const GROUPED = [
    {
      id: 'oidc-generic',
      title: 'OpenID Connect',
      schema: {
        properties: {
          issuer: { title: 'Issuer', type: 'string' },
          client_id: { title: 'Client ID', type: 'string' },
          userid_source: { title: 'User id from', type: 'string' },
          group_claim: { title: 'Group claim', type: 'string' },
          sync_groups: { title: 'Sync groups', type: 'boolean' },
        },
        required: [],
        fieldsets: [
          {
            id: 'default',
            title: 'Default',
            fields: ['issuer', 'client_id'],
          },
          { id: 'accounts', title: 'Accounts', fields: ['userid_source'] },
          {
            id: 'groups',
            title: 'Groups',
            fields: ['group_claim', 'sync_groups'],
          },
        ],
      },
    },
  ];

  it('gives each driver fieldset a tab of its own', () => {
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual([
      'default',
      'style',
      SETTINGS_FIELDSET,
      `${SETTINGS_FIELDSET}-accounts`,
      `${SETTINGS_FIELDSET}-groups`,
      MAPPING_FIELDSET,
    ]);
  });

  it("namespaces them so a driver's fieldset cannot collide with the provider's", () => {
    // The backend serves a `default` fieldset on both halves of this form,
    // and two tabs with one id is a form that renders one of them.
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);
    const ids = schema.fieldsets.map((f) => f.id);

    expect(new Set(ids).size).toBe(ids.length);
  });

  it("keeps the driver's own titles, which the backend translated", () => {
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);
    const groups = schema.fieldsets.find(
      (f) => f.id === `${SETTINGS_FIELDSET}-groups`,
    );

    expect(groups?.title).toBe('Groups');
  });

  it("labels the driver's unnamed fieldset as Settings", () => {
    // It is the one the driver did not name, so there is no title to keep.
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);
    const settings = schema.fieldsets.find((f) => f.id === SETTINGS_FIELDSET);

    expect(settings?.title).toBe('Settings');
    expect(settings?.fields).toEqual([
      `${CONFIG_PREFIX}issuer`,
      `${CONFIG_PREFIX}client_id`,
    ]);
  });

  it('prefixes every field in every fieldset', () => {
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);
    const driverTabs = schema.fieldsets.filter((f) =>
      f.id.startsWith(SETTINGS_FIELDSET),
    );

    for (const tab of driverTabs) {
      for (const field of tab.fields) {
        expect(field.startsWith(CONFIG_PREFIX)).toBe(true);
      }
    }
  });

  it('places every driver setting in exactly one tab', () => {
    // A field in no tab is invisible in the form; one in two tabs is edited
    // in two places.
    const schema = providerSchema(SERVED, GROUPED, 'oidc-generic', false, intl);
    const placed = schema.fieldsets
      .filter((f) => f.id.startsWith(SETTINGS_FIELDSET))
      .flatMap((f) => f.fields);

    expect(new Set(placed).size).toBe(placed.length);
    expect(new Set(placed)).toEqual(
      new Set(
        Object.keys(GROUPED[0].schema.properties).map(
          (name) => `${CONFIG_PREFIX}${name}`,
        ),
      ),
    );
  });

  it('still gives one tab to a driver that declares no fieldsets', () => {
    // Which is what every driver looked like before the backend grouped
    // them, and what a third-party driver that never declares one looks like
    // now.
    const schema = providerSchema(SERVED, DRIVERS, 'github', false, intl);

    expect(
      schema.fieldsets.filter((f) => f.id.startsWith(SETTINGS_FIELDSET)),
    ).toHaveLength(1);
  });
});
