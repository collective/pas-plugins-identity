/**
 * The OAuth client form, composed from what the backend already sent.
 *
 * This file used to build the schema: its own grant list, its own labels, its
 * own English. The backend serves one now, produced by `plone.restapi` from
 * `IClientRecords` — the interface the client's own storage is described by —
 * so the grants offered are exactly what the token endpoint implements, and
 * every label is translated in the site's language.
 *
 * What is left is composition and the two questions that exist only while a
 * client is being registered: the permanent `client_id`, and whether the
 * client is public. Neither is a stored field an operator edits — the first
 * becomes the record prefix and the second decides whether a secret is minted
 * — so neither is in the schema, and both disappear from the edit form.
 * @module helpers/clientSchema
 */
import { defineMessages } from 'react-intl';

import type { JsonSchema, OAuthClient, VoltoSchema } from '../types';

import type { IntlShape } from 'react-intl';

/**
 * Fields a `PATCH` may change.
 *
 * Mirrors `EDITABLE` in the backend's patch service, which refuses anything
 * else outright rather than dropping it silently. `client_id` and the auth
 * method are absent from both: changing either means registering a new
 * client, and the form says so rather than offering a field the backend
 * would reject.
 */
export const EDITABLE = [
  'title',
  'redirect_uris',
  'grant_types',
  'scope',
  'enabled',
  'service_user',
];

const messages = defineMessages({
  registration: { id: 'Registration', defaultMessage: 'Registration' },
  clientId: { id: 'Client ID', defaultMessage: 'Client ID' },
  clientIdHelp: {
    id: 'client-id-help',
    defaultMessage:
      'Permanent. It is what every token already issued is bound to, so it ' +
      'cannot be changed afterwards.',
  },
  publicClient: { id: 'Public client', defaultMessage: 'Public client' },
  publicClientHelp: {
    id: 'client-public-help',
    defaultMessage:
      'A native or browser app, which cannot keep a secret. No secret is ' +
      'minted and PKCE becomes mandatory instead.',
  },
});

/**
 * Build the client form from the schema the backend sent.
 *
 * @param served The schema from `@identity-clients`.
 * @param adding Whether this registers a client, which asks two more
 *   questions than an edit does.
 * @param intl For the labels of the two registration-only fields.
 * @returns A Volto schema.
 */
export function clientSchema(
  served: JsonSchema | undefined,
  adding: boolean,
  intl: IntlShape,
): VoltoSchema {
  const properties: Record<string, Record<string, unknown>> = {};
  const fieldsets: { id: string; title: string; fields: string[] }[] = [];
  const required = [...(served?.required ?? [])];

  if (adding) {
    properties.client_id = {
      title: intl.formatMessage(messages.clientId),
      description: intl.formatMessage(messages.clientIdHelp),
      type: 'string',
    };
    properties.public = {
      title: intl.formatMessage(messages.publicClient),
      description: intl.formatMessage(messages.publicClientHelp),
      type: 'boolean',
    };
    required.push('client_id');
  }

  Object.assign(properties, served?.properties ?? {});

  (served?.fieldsets ?? []).forEach((fieldset, index) => {
    const fields =
      index === 0
        ? [
            ...(adding ? ['client_id'] : []),
            ...fieldset.fields.filter(
              (name) => adding || EDITABLE.includes(name),
            ),
            ...(adding ? ['public'] : []),
          ]
        : fieldset.fields.filter((name) => adding || EDITABLE.includes(name));
    if (fields.length) {
      fieldsets.push({
        id: fieldset.id,
        title:
          index === 0 && adding
            ? intl.formatMessage(messages.registration)
            : fieldset.title,
        fields,
      });
    }
  });

  return { fieldsets, properties, required };
}

/**
 * Turn a client from the API into form data.
 *
 * @param client The client, or undefined when registering.
 * @returns Form data.
 */
export function toFormData(client?: OAuthClient): Record<string, unknown> {
  if (!client) {
    // `Form` seeds the rest from the schema's own defaults; what it cannot
    // know is that a new registration is meant to work, which is what the
    // authorization-code grant amounts to.
    return { grant_types: ['authorization_code'], public: false };
  }
  return {
    title: client.title ?? '',
    enabled: client.enabled ?? true,
    grant_types: [...(client.grant_types ?? [])],
    redirect_uris: [...(client.redirect_uris ?? [])],
    scope: [...(client.scope ?? [])],
    service_user: client.service_user ?? '',
  };
}

/**
 * Turn submitted form data back into the API payload.
 *
 * Shape only. Whether a redirect URI is one this server will send a browser
 * to is decided on the backend field, which refuses a fragment, a wildcard, a
 * `javascript:` scheme and plain HTTP off the loopback -- and says which. The
 * blank entries dropped below are a list widget's empty rows, not a judgement
 * about any value somebody typed.
 *
 * @param formData What the form submitted.
 * @param adding Whether this registers a client; an edit sends only what
 *   the backend accepts, since it refuses the whole request otherwise.
 * @returns The body for POST or PATCH.
 */
export function fromFormData(
  formData: Record<string, any>,
  adding: boolean,
): Record<string, unknown> {
  const data = formData ?? {};
  const payload: Record<string, unknown> = {
    title: data.title ?? '',
    grant_types: [...(data.grant_types ?? [])],
    redirect_uris: (data.redirect_uris ?? []).filter(Boolean),
    scope: (data.scope ?? []).filter(Boolean),
    service_user: data.service_user ?? '',
  };

  if (adding) {
    payload.client_id = String(data.client_id ?? '').trim();
    payload.public = Boolean(data.public);
    return payload;
  }
  payload.enabled = Boolean(data.enabled);
  // Filtered rather than assembled a second time: the backend refuses the
  // whole request when it sees a field it will not change, so the two lists
  // agreeing is what keeps an edit from failing wholesale.
  return Object.fromEntries(
    Object.entries(payload).filter(([field]) => EDITABLE.includes(field)),
  );
}
