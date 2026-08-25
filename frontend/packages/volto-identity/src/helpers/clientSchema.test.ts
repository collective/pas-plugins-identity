import { describe, expect, it } from 'vitest';

import {
  EDITABLE,
  GRANT_TYPES,
  clientSchema,
  fromFormData,
  toFormData,
} from './clientSchema';
import type { OAuthClient } from '../types';

const CLIENT: OAuthClient = {
  '@id': '/@identity-clients/app',
  client_id: 'app',
  title: 'Example App',
  redirect_uris: ['https://app.example.org/cb'],
  grant_types: ['authorization_code', 'refresh_token'],
  scope: 'openid profile email',
  auth_method: 'client_secret_post',
  public: false,
  enabled: true,
  service_user: '',
};

/** The fields of a fieldset, flattened, in the order they are rendered. */
function fields(adding: boolean): string[] {
  return clientSchema(adding).fieldsets.flatMap((fieldset) => fieldset.fields);
}

describe('clientSchema', () => {
  it('asks for the permanent id only when registering', () => {
    expect(fields(true)).toContain('client_id');
    expect(fields(false)).not.toContain('client_id');
  });

  it('requires the id it cannot invent', () => {
    expect(clientSchema(true).required).toEqual(['client_id']);
  });

  it('asks nothing an edit cannot change', () => {
    // The backend refuses the whole PATCH when it sees a field it will not
    // change, so a field offered here is a save that fails outright.
    const editable = new Set([...EDITABLE, 'client_id']);
    for (const field of fields(false)) {
      expect(editable.has(field)).toBe(true);
    }
  });

  it('offers whether a client is public only at registration', () => {
    // Turning a confidential client public would leave a stored secret hash
    // that nothing checks, so it is a re-registration rather than an edit.
    expect(fields(true)).toContain('public');
    expect(fields(false)).not.toContain('public');
  });

  it('offers enabling only on an existing client', () => {
    expect(fields(false)).toContain('enabled');
    expect(fields(true)).not.toContain('enabled');
  });

  it('offers exactly the grants the token endpoint implements', () => {
    expect(GRANT_TYPES.map(([value]) => value)).toEqual([
      'authorization_code',
      'refresh_token',
      'client_credentials',
    ]);
    expect(clientSchema(true).properties.grant_types.choices).toEqual(
      GRANT_TYPES,
    );
  });

  it('starts a registration on the grant that makes it work', () => {
    expect(clientSchema(true).properties.grant_types.default).toEqual([
      'authorization_code',
    ]);
  });

  it('edits the repeating values as lists rather than as text', () => {
    const properties = clientSchema(true).properties;

    for (const field of ['redirect_uris', 'scope']) {
      expect(properties[field].type).toBe('array');
      expect(properties[field].widget).toBe('token');
    }
  });
});

describe('toFormData', () => {
  it('seeds a registration with the grant that makes it work', () => {
    expect(toFormData()).toEqual({
      grant_types: ['authorization_code'],
      public: false,
    });
  });

  it('splits the wire scope into the permissions it is', () => {
    expect(toFormData(CLIENT).scope).toEqual(['openid', 'profile', 'email']);
  });

  it('leaves an empty scope empty rather than a blank entry', () => {
    expect(toFormData({ ...CLIENT, scope: '' }).scope).toEqual([]);
  });

  it('copies the lists rather than handing over the stored ones', () => {
    // The form mutates what it is given; the store's copy must not move.
    const data = toFormData(CLIENT);

    expect(data.redirect_uris).not.toBe(CLIENT.redirect_uris);
    expect(data.grant_types).not.toBe(CLIENT.grant_types);
  });
});

describe('fromFormData', () => {
  const draft = {
    client_id: '  app  ',
    title: '  Example App  ',
    public: true,
    grant_types: ['authorization_code'],
    redirect_uris: [' https://a.example.org/cb ', '', '  '],
    scope: ['openid', ' profile '],
    service_user: ' svc ',
  };

  it('joins the scope back into what the wire wants', () => {
    expect(fromFormData(draft, true).scope).toBe('openid profile');
  });

  it('drops the blank redirect URIs an exact match would never hit', () => {
    expect(fromFormData(draft, true).redirect_uris).toEqual([
      'https://a.example.org/cb',
    ]);
  });

  it('trims the values an operator pasted', () => {
    const payload = fromFormData(draft, true);

    expect(payload.client_id).toBe('app');
    expect(payload.title).toBe('Example App');
    expect(payload.service_user).toBe('svc');
  });

  it('sends the id and the client type only when registering', () => {
    const payload = fromFormData(draft, true);

    expect(payload.client_id).toBe('app');
    expect(payload.public).toBe(true);
  });

  it('sends an edit nothing the backend would refuse', () => {
    const payload = fromFormData({ ...draft, enabled: false }, false);

    expect(Object.keys(payload).sort()).toEqual([...EDITABLE].sort());
    expect(payload.enabled).toBe(false);
  });

  it('reads a missing enabled as disabled rather than as absent', () => {
    // The checkbox is absent from the form data when it was never touched
    // and never checked, which is a client that stays off.
    expect(fromFormData(draft, false).enabled).toBe(false);
  });

  it('survives a form that submitted nothing at all', () => {
    expect(fromFormData({}, true)).toEqual({
      client_id: '',
      title: '',
      public: false,
      grant_types: [],
      redirect_uris: [],
      scope: '',
      service_user: '',
    });
  });
});
