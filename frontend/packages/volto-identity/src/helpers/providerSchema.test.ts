import { describe, expect, it } from 'vitest';

import {
  CONFIG_PREFIX,
  fromFormData,
  orderedFields,
  propertyFor,
  providerSchema,
  toFormData,
} from './providerSchema';
import { fromRows, toRows } from './propertymap';
import { USER_FIELDS_VOCABULARY } from '../constants/vocabularies';
import type { Driver } from '../types';

const OIDC: Driver = {
  id: 'oidc-generic',
  title: 'Generic OIDC',
  schema: {
    issuer: {
      type: 'string',
      title: 'Issuer',
      secret: false,
      required: true,
      order: 10,
    },
    client_secret: {
      type: 'string',
      title: 'Client secret',
      secret: true,
      order: 30,
    },
    timeout: { type: 'int', title: 'Timeout', secret: false, order: 70 },
    auto_link: { type: 'bool', title: 'Auto link', secret: false, order: 60 },
    scope: {
      type: 'string',
      title: 'Scope',
      secret: false,
      default: 'openid email profile',
      order: 40,
    },
    allowed_groups: {
      type: 'list',
      title: 'Allowed groups',
      secret: false,
      order: 80,
    },
    userid_source: {
      type: 'choice',
      title: 'Userid taken from',
      secret: false,
      default: 'uuid',
      order: 50,
      choices: [
        ['uuid', 'A random id'],
        ['username', "The provider's username"],
      ],
    },
  },
};

const GITHUB: Driver = { id: 'github', title: 'GitHub', schema: {} };

describe('propertyFor', () => {
  it('renders a secret with the password widget', () => {
    expect(propertyFor(OIDC.schema.client_secret).widget).toBe('password');
  });

  it('renders an int as a number', () => {
    expect(propertyFor(OIDC.schema.timeout).type).toBe('number');
  });

  it('renders a bool as a boolean', () => {
    expect(propertyFor(OIDC.schema.auto_link).type).toBe('boolean');
  });

  it('renders anything else as text', () => {
    expect(propertyFor(OIDC.schema.issuer).type).toBe('string');
  });

  it('renders a list as a repeating value, not a text box', () => {
    // Typing several groups into one input and hoping they are split is
    // exactly the failure this avoids.
    expect(propertyFor(OIDC.schema.allowed_groups)).toMatchObject({
      type: 'array',
      widget: 'token',
    });
  });

  it('renders a choice as a select over the options the driver names', () => {
    expect(propertyFor(OIDC.schema.userid_source).choices).toEqual([
      ['uuid', 'A random id'],
      ['username', "The provider's username"],
    ]);
  });

  it("carries the driver's default into the form", () => {
    // A blank scope field is how a GitHub provider ends up configured with
    // OIDC scopes and never sees an email address.
    expect(propertyFor(OIDC.schema.scope).default).toBe('openid email profile');
  });

  it('omits default entirely when the driver declares none', () => {
    expect('default' in propertyFor(OIDC.schema.issuer)).toBe(false);
  });

  it('carries the driver description through', () => {
    expect(
      propertyFor({
        type: 'string',
        title: 'X',
        description: 'why',
        secret: false,
      }).description,
    ).toBe('why');
  });
});

describe('orderedFields', () => {
  it('sorts on the position the driver declared, not the key', () => {
    // What arrives from the server is alphabetical -- plone.restapi
    // serialises a schema with sorted keys -- so auto_link would otherwise
    // render above issuer and client_secret.
    expect(orderedFields(OIDC.schema).map(([name]) => name)).toEqual([
      'issuer',
      'client_secret',
      'scope',
      'userid_source',
      'auto_link',
      'timeout',
      'allowed_groups',
    ]);
  });

  it('sinks a field that declares no position, rather than dropping it', () => {
    const schema = {
      late: { type: 'string', title: 'Late', secret: false },
      early: { type: 'string', title: 'Early', secret: false, order: 10 },
    };

    expect(orderedFields(schema).map(([name]) => name)).toEqual([
      'early',
      'late',
    ]);
  });

  it('breaks a tie by name, so the result is stable', () => {
    const schema = {
      b: { type: 'string', title: 'B', secret: false, order: 10 },
      a: { type: 'string', title: 'A', secret: false, order: 10 },
    };

    expect(orderedFields(schema).map(([name]) => name)).toEqual(['a', 'b']);
  });
});

describe('providerSchema', () => {
  it('asks for an id and a driver only when adding', () => {
    const adding = providerSchema([OIDC], 'oidc-generic', true);
    const editing = providerSchema([OIDC], 'oidc-generic', false);

    expect(adding.properties.id).toBeTruthy();
    expect(adding.required).toContain('id');
    expect(editing.properties.id).toBeUndefined();
  });

  it('offers every installed driver as a choice', () => {
    const schema = providerSchema([OIDC, GITHUB], undefined, true);

    expect(schema.properties.driver.choices).toEqual([
      ['oidc-generic', 'Generic OIDC'],
      ['github', 'GitHub'],
    ]);
  });

  it('asks which driver before asking anything about it', () => {
    // The driver decides which fields the rest of the form has at all.
    const schema = providerSchema([OIDC], 'oidc-generic', true);

    expect(schema.fieldsets[0].fields).toEqual([
      'driver',
      'id',
      'title',
      'enabled',
    ]);
  });

  it("renders the driver's settings in the order it asked for", () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true);
    const settings = schema.fieldsets.find((f) => f.id === 'settings');

    expect(settings?.fields).toEqual([
      `${CONFIG_PREFIX}issuer`,
      `${CONFIG_PREFIX}client_secret`,
      `${CONFIG_PREFIX}scope`,
      `${CONFIG_PREFIX}userid_source`,
      `${CONFIG_PREFIX}auto_link`,
      `${CONFIG_PREFIX}timeout`,
      `${CONFIG_PREFIX}allowed_groups`,
    ]);
  });

  it('renders the chosen driver fields, namespaced', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true);

    expect(schema.properties[`${CONFIG_PREFIX}issuer`]).toBeTruthy();
    // Namespaced so a driver cannot collide with title or enabled.
    expect(schema.properties.issuer).toBeUndefined();
  });

  it('carries the driver required flags into the schema', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', false);

    expect(schema.required).toContain(`${CONFIG_PREFIX}issuer`);
    expect(schema.required).not.toContain(`${CONFIG_PREFIX}timeout`);
  });

  it('shows no settings fieldset before a driver is chosen', () => {
    // An empty fieldset reads as a broken form.
    const schema = providerSchema([OIDC], undefined, true);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });

  it('shows no settings fieldset for a driver that declares none', () => {
    const schema = providerSchema([GITHUB], 'github', true);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });

  it('titles the settings fieldset after the driver', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true);

    expect(schema.fieldsets[1]).toMatchObject({
      id: 'settings',
      title: 'Generic OIDC',
    });
  });

  it('takes the user field from the vocabulary', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true);
    const rows = schema.properties.propertymap as any;

    expect(rows.widget).toBe('object_list');
    expect(rows.schema.properties.field.vocabulary).toEqual({
      '@id': USER_FIELDS_VOCABULARY,
    });
    // Claim names come from the provider, so no vocabulary can know them.
    expect(rows.schema.properties.claim.vocabulary).toBeUndefined();
  });

  it('survives a driver that is not installed', () => {
    const schema = providerSchema([], 'gone', false);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });
});

describe('toFormData', () => {
  it('defaults a new provider to enabled with no mapping', () => {
    expect(toFormData(undefined, toRows)).toEqual({
      enabled: true,
      propertymap: [],
    });
  });

  it('flattens config onto prefixed keys', () => {
    const data = toFormData(
      { title: 'Dex', enabled: true, config: { issuer: 'http://dex' } },
      toRows,
    );

    expect(data[`${CONFIG_PREFIX}issuer`]).toBe('http://dex');
  });

  it('turns the stored mapping into rows', () => {
    const data = toFormData(
      { config: {}, propertymap: { login: 'username' } },
      toRows,
    );

    expect(data.propertymap).toEqual([
      { '@id': expect.any(String), claim: 'login', field: 'username' },
    ]);
  });
});

describe('fromFormData', () => {
  it('nests the prefixed keys back under config', () => {
    const payload = fromFormData(
      { title: 'Dex', enabled: true, [`${CONFIG_PREFIX}issuer`]: 'http://dex' },
      fromRows,
    );

    expect(payload.config).toEqual({ issuer: 'http://dex' });
    expect(payload.title).toBe('Dex');
  });

  it('turns rows back into a mapping', () => {
    const payload = fromFormData(
      { propertymap: [{ '@id': 'a', claim: 'login', field: 'username' }] },
      fromRows,
    );

    expect(payload.propertymap).toEqual({ login: 'username' });
  });

  it('drops the @id Volto adds to form data', () => {
    const payload = fromFormData({ '@id': '/somewhere', title: 'X' }, fromRows);

    expect(payload['@id']).toBeUndefined();
  });

  it('trims the id and the title', () => {
    const payload = fromFormData({ id: '  dex  ', title: '  Dex  ' }, fromRows);

    expect(payload.id).toBe('dex');
    expect(payload.title).toBe('Dex');
  });

  it('always sends config, even when the driver has no fields', () => {
    // Otherwise a PATCH would leave the previous config in place rather
    // than reflecting what the form showed.
    expect(fromFormData({ title: 'X' }, fromRows).config).toEqual({});
  });

  it('coerces enabled to a boolean', () => {
    expect(fromFormData({}, fromRows).enabled).toBe(false);
    expect(fromFormData({ enabled: true }, fromRows).enabled).toBe(true);
  });
});
