/**
 * The client form is composed, not invented.
 *
 * What used to be asserted here — which grants exist, what each field is
 * called, which of them are text boxes — is the backend's answer now,
 * serialized by `plone.restapi` from `IClientRecords`. So the grants offered
 * are exactly what the token endpoint implements, without this file holding a
 * list that could drift from it.
 *
 * What is left to test is the composition, and the two questions that exist
 * only while a client is being registered.
 */
import { describe, expect, it } from 'vitest';

import {
  EDITABLE,
  clientSchema,
  fromFormData,
  toFormData,
} from './clientSchema';
import type { OAuthClient } from '../types';

const intl = {
  formatMessage: (m: { defaultMessage: string }) => m.defaultMessage,
} as any;

/** What `@identity-clients` sends: `IClientRecords`, serialized. */
const SERVED = {
  type: 'object',
  properties: {
    title: { title: 'Title', type: 'string' },
    enabled: { title: 'Enabled', type: 'boolean' },
    redirect_uris: { title: 'Redirect URIs', type: 'array', widget: 'token' },
    grant_types: {
      title: 'Grants',
      type: 'array',
      choices: [
        ['authorization_code', 'authorization_code'],
        ['client_credentials', 'client_credentials'],
        ['refresh_token', 'refresh_token'],
      ],
    },
    scope: { title: 'Scope', type: 'string' },
    service_user: { title: 'Acts as', type: 'string' },
  },
  required: ['title'],
  fieldsets: [
    { id: 'default', title: 'Default', fields: ['title', 'enabled'] },
    {
      id: 'flow',
      title: 'Flow',
      fields: ['redirect_uris', 'grant_types', 'scope', 'service_user'],
    },
  ],
};

describe('clientSchema', () => {
  it('carries the served properties through untouched', () => {
    const schema = clientSchema(SERVED, false, intl);

    expect(schema.properties.grant_types).toEqual(
      SERVED.properties.grant_types,
    );
  });

  it('offers exactly the grants the backend implements', () => {
    // Not a list this file keeps in step by hand. The vocabulary is built on
    // the backend from what the token endpoint serves and what discovery
    // advertises, so the three can no longer disagree.
    const schema = clientSchema(SERVED, true, intl);

    expect(
      (schema.properties.grant_types as any).choices.map(
        ([value]: [string, string]) => value,
      ),
    ).toEqual(['authorization_code', 'client_credentials', 'refresh_token']);
  });

  it('asks for the permanent id only when registering', () => {
    expect(clientSchema(SERVED, true, intl).properties.client_id).toBeTruthy();
    expect(
      clientSchema(SERVED, false, intl).properties.client_id,
    ).toBeUndefined();
  });

  it('requires the id it cannot invent', () => {
    expect(clientSchema(SERVED, true, intl).required).toContain('client_id');
  });

  it('offers whether a client is public only at registration', () => {
    // It decides whether a secret is minted, which is a fact about
    // registration rather than a setting.
    expect(clientSchema(SERVED, true, intl).properties.public).toBeTruthy();
    expect(clientSchema(SERVED, false, intl).properties.public).toBeUndefined();
  });

  it('asks nothing an edit cannot change', () => {
    const schema = clientSchema(SERVED, false, intl);
    const offered = schema.fieldsets.flatMap((f) => f.fields);

    expect(offered.every((field) => EDITABLE.includes(field))).toBe(true);
  });

  it('survives a backend that sent no schema', () => {
    // An empty form is recoverable; a crash on `schema.fieldsets` is not.
    const schema = clientSchema(undefined, true, intl);

    expect(schema.fieldsets).toEqual([]);
  });
});

describe('toFormData', () => {
  it('starts a registration on the grant that makes it work', () => {
    expect(toFormData().grant_types).toEqual(['authorization_code']);
  });

  it('edits a scope as the list of permissions it is', () => {
    const client = { scope: 'openid profile email' } as OAuthClient;

    expect(toFormData(client).scope).toEqual(['openid', 'profile', 'email']);
  });
});

describe('fromFormData', () => {
  it('joins the scope back into what OAuth 2 puts on the wire', () => {
    const payload = fromFormData({ scope: ['openid', 'email'] }, true);

    expect(payload.scope).toBe('openid email');
  });

  it('drops a list widget’s empty rows', () => {
    const payload = fromFormData(
      { redirect_uris: ['https://a.example/cb', '', null] },
      true,
    );

    expect(payload.redirect_uris).toEqual(['https://a.example/cb']);
  });

  it('does not judge a redirect URI', () => {
    // Whether this server will send a browser there is decided on the backend
    // field, which refuses it and says why. Correcting it here would only
    // hide which value the refusal is about.
    const payload = fromFormData(
      { redirect_uris: ['  https://a.example/cb#frag  '] },
      true,
    );

    expect(payload.redirect_uris).toEqual(['  https://a.example/cb#frag  ']);
  });

  it('sends only what a PATCH accepts', () => {
    // The backend refuses the whole request when it sees a field it will not
    // change, so the two lists agreeing is what keeps an edit from failing
    // wholesale.
    const payload = fromFormData({ title: 'x', client_id: 'nope' }, false);

    expect(payload.client_id).toBeUndefined();
    expect(Object.keys(payload).every((k) => EDITABLE.includes(k))).toBe(true);
  });
});
