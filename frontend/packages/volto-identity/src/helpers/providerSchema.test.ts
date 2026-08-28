import { testIntl } from '../testing';
import { describe, expect, it } from 'vitest';
import { createIntl } from 'react-intl';

import {
  CONFIG_PREFIX,
  fromFormData,
  orderedFields,
  propertyFor,
  suggestedProviderId,
  providerSchema,
  toFormData,
} from './providerSchema';
import {
  GROUPS_VOCABULARY,
  USER_FIELDS_VOCABULARY,
} from '../constants/vocabularies';
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

/**
 * A driver whose providers have groups.
 *
 * The backend says so by putting a `group_claim` field in the schema, and
 * that is the same switch the form reads. GITHUB above is the other case.
 */
const WITH_GROUPS: Driver = {
  id: 'keycloak',
  title: 'Keycloak',
  schema: {
    group_claim: {
      type: 'string',
      title: 'Groups arrive in the claim',
      secret: false,
      default: 'groups',
      order: 80,
    },
  },
};

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

describe('suggestedProviderId', () => {
  it('names the provider after the driver', () => {
    expect(suggestedProviderId([OIDC, GITHUB], 'github')).toBe('github');
  });

  it('slugifies a title that is not already one', () => {
    expect(suggestedProviderId([OIDC], 'oidc-generic')).toBe('generic-oidc');
  });

  it('turns punctuation into separators rather than dropping it', () => {
    // signinbeta would be a worse id than sign-in-beta, not a shorter one.
    const driver = { id: 'x', title: 'Sign in (beta)', schema: {} };

    expect(suggestedProviderId([driver], 'x')).toBe('sign-in-beta');
  });

  it("falls back to the driver's own id when the title slugifies to nothing", () => {
    const driver = { id: 'kerberos', title: '???', schema: {} };

    expect(suggestedProviderId([driver], 'kerberos')).toBe('kerberos');
  });

  it('suggests nothing before a driver is chosen', () => {
    expect(suggestedProviderId([OIDC], undefined)).toBe('');
    expect(suggestedProviderId([OIDC], 'no-such-driver')).toBe('');
  });
});

describe('toFormData seeding', () => {
  it("seeds a new provider's mapping from the driver", () => {
    const data = toFormData(undefined, {
      propertymap: { email: 'email', fullname: 'fullname' },
    });

    // The rows also carry the `@id` the list widget keys on; what matters
    // here is that the driver's pairs arrived, in its own order.
    expect(data.propertymap).toMatchObject([
      { claim: 'email', field: 'email' },
      { claim: 'fullname', field: 'fullname' },
    ]);
  });

  it('seeds nothing when the driver declares no mapping', () => {
    expect(toFormData(undefined).propertymap).toEqual([]);
  });

  it("leaves an existing provider's own mapping alone", () => {
    // Including the deliberate decision to have none: a stored provider is
    // the whole truth about itself, and a seed here would resurrect rows
    // somebody removed on purpose.
    const data = toFormData(
      { propertymap: {} },
      { propertymap: { email: 'email' } },
    );

    expect(data.propertymap).toEqual([]);
  });
});

describe('providerSchema', () => {
  it('asks for an id and a driver only when adding', () => {
    const adding = providerSchema([OIDC], 'oidc-generic', true, testIntl);
    const editing = providerSchema([OIDC], 'oidc-generic', false, testIntl);

    expect(adding.properties.id).toBeTruthy();
    expect(adding.required).toContain('id');
    expect(editing.properties.id).toBeUndefined();
  });

  it('offers every installed driver as a choice', () => {
    const schema = providerSchema([OIDC, GITHUB], undefined, true, testIntl);

    expect(schema.properties.driver.choices).toEqual([
      ['oidc-generic', 'Generic OIDC'],
      ['github', 'GitHub'],
    ]);
  });

  it('asks which driver before asking anything about it', () => {
    // The driver decides which fields the rest of the form has at all.
    const schema = providerSchema([OIDC], 'oidc-generic', true, testIntl);

    expect(schema.fieldsets[0].fields).toEqual([
      'driver',
      'id',
      'title',
      'enabled',
    ]);
  });

  it("renders the driver's settings in the order it asked for", () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, testIntl);
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
    const schema = providerSchema([OIDC], 'oidc-generic', true, testIntl);

    expect(schema.properties[`${CONFIG_PREFIX}issuer`]).toBeTruthy();
    // Namespaced so a driver cannot collide with title or enabled.
    expect(schema.properties.issuer).toBeUndefined();
  });

  it('carries the driver required flags into the schema', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', false, testIntl);

    expect(schema.required).toContain(`${CONFIG_PREFIX}issuer`);
    expect(schema.required).not.toContain(`${CONFIG_PREFIX}timeout`);
  });

  it('shows no settings fieldset before a driver is chosen', () => {
    // An empty fieldset reads as a broken form.
    const schema = providerSchema([OIDC], undefined, true, testIntl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });

  it('shows no settings fieldset for a driver that declares none', () => {
    const schema = providerSchema([GITHUB], 'github', true, testIntl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });

  it('titles the settings fieldset after the driver', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, testIntl);

    expect(schema.fieldsets[1]).toMatchObject({
      id: 'settings',
      title: 'Generic OIDC',
    });
  });

  it('takes the user field from the vocabulary', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, testIntl);
    const rows = schema.properties.propertymap as any;

    expect(rows.widget).toBe('object_list');
    expect(rows.schema.properties.field.vocabulary).toEqual({
      '@id': USER_FIELDS_VOCABULARY,
    });
    // Claim names come from the provider, so no vocabulary can know them.
    expect(rows.schema.properties.claim.vocabulary).toBeUndefined();
  });

  it('survives a driver that is not installed', () => {
    const schema = providerSchema([], 'gone', false, testIntl);

    expect(schema.fieldsets.map((f) => f.id)).toEqual(['default', 'mapping']);
  });
});

describe('toFormData', () => {
  it('defaults a new provider to enabled with no mapping', () => {
    expect(toFormData(undefined)).toEqual({
      enabled: true,
      propertymap: [],
      groupmap: [],
    });
  });

  it('flattens config onto prefixed keys', () => {
    const data = toFormData({
      title: 'Dex',
      enabled: true,
      config: { issuer: 'http://dex' },
    });

    expect(data[`${CONFIG_PREFIX}issuer`]).toBe('http://dex');
  });

  it('turns the stored mapping into rows', () => {
    const data = toFormData({
      config: {},
      propertymap: { login: 'username' },
    });

    expect(data.propertymap).toEqual([
      { '@id': expect.any(String), claim: 'login', field: 'username' },
    ]);
  });
});

describe('fromFormData', () => {
  it('nests the prefixed keys back under config', () => {
    const payload = fromFormData({
      title: 'Dex',
      enabled: true,
      [`${CONFIG_PREFIX}issuer`]: 'http://dex',
    });

    expect(payload.config).toEqual({ issuer: 'http://dex' });
    expect(payload.title).toBe('Dex');
  });

  it('turns rows back into a mapping', () => {
    const payload = fromFormData({
      propertymap: [{ '@id': 'a', claim: 'login', field: 'username' }],
    });

    expect(payload.propertymap).toEqual({ login: 'username' });
  });

  it('drops the @id Volto adds to form data', () => {
    const payload = fromFormData({ '@id': '/somewhere', title: 'X' });

    expect(payload['@id']).toBeUndefined();
  });

  it('trims the id and the title', () => {
    const payload = fromFormData({ id: '  dex  ', title: '  Dex  ' });

    expect(payload.id).toBe('dex');
    expect(payload.title).toBe('Dex');
  });

  it('always sends config, even when the driver has no fields', () => {
    // Otherwise a PATCH would leave the previous config in place rather
    // than reflecting what the form showed.
    expect(fromFormData({ title: 'X' }).config).toEqual({});
  });

  it('coerces enabled to a boolean', () => {
    expect(fromFormData({}).enabled).toBe(false);
    expect(fromFormData({ enabled: true }).enabled).toBe(true);
  });
});

describe('the group mapping', () => {
  it('is offered for a driver whose providers have groups', () => {
    const schema = providerSchema([WITH_GROUPS], 'keycloak', false, testIntl);

    expect(schema.properties.groupmap).toBeTruthy();
    expect(schema.fieldsets.at(-1).fields).toEqual(['propertymap', 'groupmap']);
  });

  it('is not offered for a driver that has none', () => {
    // Asking an operator to map the groups of a magic link is asking a
    // question with no answer. The backend applies the same switch: a map
    // stored against such a provider grants nothing.
    const schema = providerSchema([GITHUB], 'github', false, testIntl);

    expect(schema.properties.groupmap).toBeUndefined();
    expect(schema.fieldsets.at(-1).fields).toEqual(['propertymap']);
  });

  it('is not offered before a driver is chosen', () => {
    const schema = providerSchema([WITH_GROUPS], undefined, true, testIntl);

    expect(schema.properties.groupmap).toBeUndefined();
  });

  it('picks the local group from a vocabulary, and takes the other as text', () => {
    // The halves are not symmetric. This site cannot enumerate the far end's
    // directory, but a local group that does not exist grants nothing -- so
    // the side we can check is the side we make a picker.
    const { schema } = providerSchema(
      [WITH_GROUPS],
      'keycloak',
      false,
      testIntl,
    ).properties.groupmap as any;

    expect(schema.properties.local.vocabulary).toEqual({
      '@id': GROUPS_VOCABULARY,
    });
    expect(schema.properties.group.type).toBe('string');
    expect(schema.properties.group.vocabulary).toBeUndefined();
  });

  it('seeds a new provider from the driver', () => {
    const data = toFormData(undefined, {
      groupmap: { editors: 'site-editors' },
    });

    expect(data.groupmap).toMatchObject([
      { group: 'editors', local: 'site-editors' },
    ]);
  });

  it("leaves an existing provider's own map alone", () => {
    const data = toFormData(
      { groupmap: {} },
      { groupmap: { editors: 'site-editors' } },
    );

    expect(data.groupmap).toEqual([]);
  });

  it('turns the stored map into rows and back', () => {
    const data = toFormData({ config: {}, groupmap: { editors: 'staff' } });

    expect(data.groupmap).toEqual([
      { '@id': expect.any(String), group: 'editors', local: 'staff' },
    ]);
    expect(fromFormData({ groupmap: data.groupmap }).groupmap).toEqual({
      editors: 'staff',
    });
  });
});

describe('the schema is translatable', () => {
  // Proof rather than inspection: a catalogue that overrides the ids gives
  // different labels back. Reading the English out again would pass just as
  // well with every string hardcoded, which is what this replaces.
  const pt = createIntl({
    locale: 'pt-BR',
    defaultLocale: 'en',
    onError: () => {},
    messages: {
      Title: 'Título',
      Mapping: 'Mapeamento',
      'Add a provider': 'Adicionar um provedor',
      'Attribute mapping': 'Mapeamento de atributos',
      'Provider claim': 'Claim do provedor',
    },
  });

  it('translates a field title', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, pt);

    expect(schema.properties.title.title).toBe('Título');
  });

  it('translates the form title', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, pt);

    expect(schema.title).toBe('Adicionar um provedor');
  });

  it('translates a fieldset title', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, pt);
    const mapping = schema.fieldsets.find((f) => f.id === 'mapping');

    expect(mapping?.title).toBe('Mapeamento');
  });

  it('translates the mapping widget and its rows', () => {
    const schema = providerSchema([OIDC], 'oidc-generic', true, pt);
    const propertymap = schema.properties.propertymap as any;

    expect(propertymap.title).toBe('Mapeamento de atributos');
    expect(propertymap.schema.properties.claim.title).toBe('Claim do provedor');
  });

  it("leaves a driver's own field labels as the backend sent them", () => {
    // They arrive over `@identity-drivers` as plain strings rather than
    // message ids, so nothing here can translate them. Asserted so the
    // limitation is visible rather than discovered.
    const schema = providerSchema([OIDC], 'oidc-generic', true, pt);

    expect(schema.properties[`${CONFIG_PREFIX}issuer`].title).toBe(
      OIDC.schema.issuer.title,
    );
  });
});
