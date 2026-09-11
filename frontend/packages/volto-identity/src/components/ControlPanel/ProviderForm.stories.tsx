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
 * The provider form on its own, without the panel around it.
 *
 * The panel's own stories open this form at its route, but they show it
 * inside the page. Rendering the schema straight into Volto's `Form` isolates
 * the two mapping editors, which is what these stories are about.
 *
 * Both mappings are `object_list` widgets, and one sub-field of one of them
 * reads a vocabulary over the API: the property map's target, which is a
 * picker over the four Profile fields a login writes. Every story carries the
 * loaded vocabularies in its store, so that picker renders its terms rather
 * than empty -- which is also exactly how it looks when the backend refuses
 * `@vocabularies`, and is worth recognising.
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
 * The **Attribute mapping** fieldset carries both editors, and the asymmetry
 * between them is the thing to look at. A claim path and a provider-side
 * group are text, because neither can be enumerated from here. A property
 * map's target is a picker over the four Profile fields a login writes. A
 * local group is text as well, though this site does know its own groups: a
 * profile may ship a map before the group it points at, and the login skips a
 * row it cannot resolve rather than the import refusing the map.
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
