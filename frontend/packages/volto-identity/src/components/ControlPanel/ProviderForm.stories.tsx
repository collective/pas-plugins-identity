import { testIntl } from '../../testing';
import type { Meta, StoryObj } from '@storybook/react';

import { Form } from '@plone/volto/components/manage/Form';

import {
  CONFIGURED,
  DRIVERS,
  GROUPS_STATE,
  PROVIDER_SCHEMA,
  USER_FIELDS_STATE,
  withStore,
} from '../../stories/fixtures';
import { providerSchema, toFormData } from '../../helpers/providerSchema';

/**
 * The provider form on its own, which the panel's stories cannot show.
 *
 * `ProvidersControlPanel` opens this form from `useState`, so there is no
 * prop or store value a story could set to reach it -- and the listing next
 * to it renders a provider's title, id, driver and enabled flag, none of
 * which say anything about its mappings. Rendering the schema straight into
 * Volto's `Form` is what makes the two mapping editors visible.
 *
 * Both mappings are `object_list` widgets whose sub-fields read a vocabulary
 * over the API, so every story here carries the loaded vocabularies in its
 * store. Without them the pickers render empty, which is also exactly how
 * this looks when the backend refuses `@vocabularies` -- worth recognising.
 */
const meta: Meta<typeof Form> = {
  title: 'Identity/ControlPanel/ProviderForm',
  component: Form,
};
export default meta;

type Story = StoryObj<typeof Form>;

const store = {
  vocabularies: { ...USER_FIELDS_STATE, ...GROUPS_STATE },
};

/** The Keycloak provider from the fixtures: OIDC, and it has groups. */
const KEYCLOAK = CONFIGURED[0];

/** The GitHub provider: its driver declares no group claim. */
const GITHUB = CONFIGURED[1];

const form = (provider: (typeof CONFIGURED)[number], driverId: string) => ({
  schema: providerSchema(PROVIDER_SCHEMA, DRIVERS, driverId, false, testIntl),
  formData: toFormData(provider),
  onSubmit: () => {},
  onCancel: () => {},
  hideActions: true,
});

/**
 * A provider whose driver has groups.
 *
 * The **Attribute mapping** fieldset carries both editors. The group map's
 * provider side is free text and its local side is a picker: this site
 * cannot enumerate the far end's directory, but it knows its own groups, and
 * a local group that does not exist grants nothing.
 */
export const WithGroups: Story = {
  args: form(KEYCLOAK, 'oidc-generic'),
  decorators: [withStore(store)],
};

/**
 * A provider whose driver has none.
 *
 * The group map is absent, not empty. The backend declares a driver's group
 * support by putting a `group_claim` field in its config schema, and the form
 * reads that same switch -- so nobody is asked to map the groups of a
 * provider that has none.
 */
export const WithoutGroups: Story = {
  args: form(GITHUB, 'github'),
  decorators: [withStore(store)],
};

/**
 * Adding a provider, before anything has been mapped.
 *
 * The group map starts empty and grants nothing until somebody fills it in.
 * That is the whole of the safety story: a provider asserting groups on a
 * site that has not mapped them changes nobody's access.
 */
export const Adding: Story = {
  args: {
    schema: providerSchema(
      PROVIDER_SCHEMA,
      DRIVERS,
      'oidc-generic',
      true,
      testIntl,
    ),
    formData: toFormData(undefined, {
      propertymap: DRIVERS[0].default_propertymap,
      groupmap: DRIVERS[0].default_groupmap,
    }),
    onSubmit: () => {},
    onCancel: () => {},
    hideActions: true,
  },
  decorators: [withStore(store)],
};
