/**
 * Build the Volto form schema for an OAuth client registration.
 *
 * The providers panel gets its fields from the driver, which describes
 * itself over `@identity-drivers`. A client has no such describing thing --
 * the registry is this package's own and its fields are fixed by the OAuth
 * spec rather than by an add-on -- so they are enumerated here. What is
 * shared with the providers panel is everything after that: one schema, one
 * Volto `Form`, and no input laid out by hand.
 * @module helpers/clientSchema
 */
import { defineMessages } from 'react-intl';
import type { IntlShape } from 'react-intl';
import type { VoltoSchema } from './providerSchema';
import type { OAuthClient } from '../types';

/**
 * Every grant the token endpoint implements.
 *
 * Mirrors `GRANT_TYPES` in the server layer, which is also what the
 * discovery document advertises. Hardcoded rather than read from discovery
 * because a grant this form offers and the endpoint does not implement is a
 * registration that fails at the first token request -- so the two lists
 * being the same is a fact worth stating in one place per side rather than
 * fetching over the network to find out.
 */
export const GRANT_TYPES: [string, string][] = [
  ['authorization_code', 'Authorization code'],
  ['refresh_token', 'Refresh token'],
  ['client_credentials', 'Client credentials'],
];

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

/**
 * Build the schema for registering or editing a client.
 *
 * @param adding Whether this is the registration form, which also asks for
 *   the permanent id and whether the client is public.
 * @returns The schema.
 */
const messages = defineMessages({
  clientId: { id: 'Client ID', defaultMessage: 'Client ID' },
  clientIdHelp: {
    id: 'client-id-help',
    defaultMessage:
      'Permanent. Every token minted for this client carries it as the ' +
      'audience, so renaming it later would strand them all.',
  },
  title: { id: 'Title', defaultMessage: 'Title' },
  titleHelp: {
    id: 'client-title-help',
    defaultMessage: 'What the consent screen calls this client.',
  },
  publicClient: { id: 'Public client', defaultMessage: 'Public client' },
  publicClientHelp: {
    id: 'public-client-help',
    defaultMessage:
      'A browser or native app, which cannot keep a secret. PKCE is ' +
      'required for these and no secret is issued. Not editable ' +
      'afterwards: turning a confidential client public would leave a ' +
      'stored secret hash that nothing checks.',
  },
  enabled: { id: 'Enabled', defaultMessage: 'Enabled' },
  enabledHelp: {
    id: 'client-enabled-help',
    defaultMessage:
      'A disabled client is refused at every endpoint, and its existing ' +
      'access tokens are refused as well: the audience is checked against ' +
      'this registry on every request.',
  },
  grants: { id: 'Grants', defaultMessage: 'Grants' },
  grantsHelp: {
    id: 'client-grants-help',
    defaultMessage:
      'Which flows this client may use. A grant is refused at the token ' +
      'endpoint unless it is listed here.',
  },
  redirectUris: { id: 'Redirect URIs', defaultMessage: 'Redirect URIs' },
  redirectUrisHelp: {
    id: 'redirect-uris-help',
    defaultMessage:
      'Matched exactly -- a trailing slash or an extra query parameter is ' +
      'a different URI. A client using the authorization code grant needs ' +
      'at least one.',
  },
  scope: { id: 'Scope', defaultMessage: 'Scope' },
  scopeHelp: {
    id: 'client-scope-help',
    defaultMessage:
      'The most this client may ever be granted, one entry per token. A ' +
      'request for more is cut down to this rather than refused.',
  },
  serviceUser: { id: 'Service user', defaultMessage: 'Service user' },
  serviceUserHelp: {
    id: 'service-user-help',
    defaultMessage:
      'The Plone userid a client-credentials token acts as. Only that ' +
      'grant uses it; leave it empty for a client that signs people in.',
  },
  registerClient: {
    id: 'Register a client',
    defaultMessage: 'Register a client',
  },
  editClient: { id: 'Edit client', defaultMessage: 'Edit client' },
  client: { id: 'Client', defaultMessage: 'Client' },
  access: { id: 'Access', defaultMessage: 'Access' },
});

export function clientSchema(adding: boolean, intl: IntlShape): VoltoSchema {
  const properties: Record<string, Record<string, unknown>> = {};
  const identity: string[] = [];

  if (adding) {
    properties.client_id = {
      title: intl.formatMessage(messages.clientId),
      description: intl.formatMessage(messages.clientIdHelp),
      type: 'string',
    };
    identity.push('client_id');
  }

  properties.title = {
    title: intl.formatMessage(messages.title),
    description: intl.formatMessage(messages.titleHelp),
    type: 'string',
  };
  identity.push('title');

  if (adding) {
    properties.public = {
      title: intl.formatMessage(messages.publicClient),
      description: intl.formatMessage(messages.publicClientHelp),
      type: 'boolean',
    };
    identity.push('public');
  } else {
    properties.enabled = {
      title: intl.formatMessage(messages.enabled),
      description: intl.formatMessage(messages.enabledHelp),
      type: 'boolean',
    };
    identity.push('enabled');
  }

  properties.grant_types = {
    title: intl.formatMessage(messages.grants),
    description: intl.formatMessage(messages.grantsHelp),
    type: 'array',
    choices: GRANT_TYPES,
    default: ['authorization_code'],
  };
  properties.redirect_uris = {
    title: intl.formatMessage(messages.redirectUris),
    description: intl.formatMessage(messages.redirectUrisHelp),
    type: 'array',
    widget: 'token',
  };
  properties.scope = {
    title: intl.formatMessage(messages.scope),
    description: intl.formatMessage(messages.scopeHelp),
    type: 'array',
    widget: 'token',
  };
  properties.service_user = {
    title: intl.formatMessage(messages.serviceUser),
    description: intl.formatMessage(messages.serviceUserHelp),
    type: 'string',
  };

  return {
    title: intl.formatMessage(
      adding ? messages.registerClient : messages.editClient,
    ),
    fieldsets: [
      {
        id: 'default',
        title: intl.formatMessage(messages.client),
        fields: identity,
      },
      {
        id: 'access',
        title: intl.formatMessage(messages.access),
        fields: ['grant_types', 'redirect_uris', 'scope', 'service_user'],
      },
    ],
    properties,
    required: adding ? ['client_id'] : [],
  };
}

/**
 * Seed a form from a stored client.
 *
 * @param client The client being edited, or undefined when registering.
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
    // A scope arrives as the space-joined string OAuth 2 puts on the wire
    // and is edited as the list of permissions it actually is -- the same
    // reason a provider's scope is a list rather than one text box.
    scope: (client.scope ?? '').split(/\s+/).filter(Boolean),
    service_user: client.service_user ?? '',
  };
}

/**
 * Turn submitted form data back into the API payload.
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
    title: String(data.title ?? '').trim(),
    grant_types: [...(data.grant_types ?? [])],
    // Blank entries and stray whitespace have to go: matching is exact on
    // the backend, so a URI with a space in it is a URI nothing matches.
    redirect_uris: (data.redirect_uris ?? [])
      .map((uri: string) => String(uri).trim())
      .filter(Boolean),
    scope: (data.scope ?? [])
      .map((token: string) => String(token).trim())
      .filter(Boolean)
      .join(' '),
    service_user: String(data.service_user ?? '').trim(),
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
