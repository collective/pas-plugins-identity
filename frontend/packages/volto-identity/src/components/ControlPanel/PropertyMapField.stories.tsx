import type { Meta, StoryObj } from '@storybook/react';

import PropertyMapField from './PropertyMapField';
import { toRows } from '../../helpers/propertymap';
import { USER_FIELDS_STATE, withStore } from '../../stories/fixtures';

const meta: Meta<typeof PropertyMapField> = {
  title: 'Identity/ControlPanel/PropertyMapField',
  component: PropertyMapField,
  decorators: [withStore({ vocabularies: USER_FIELDS_STATE })],
  args: {
    id: 'propertymap',
    rows: toRows({
      preferred_username: 'username',
      'address.formatted': 'location',
    }),
    onChange: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof PropertyMapField>;

export const Mapped: Story = {};

/** What a provider looks like before anyone maps anything. */
export const Empty: Story = { args: { rows: [] } };

export const Disabled: Story = { args: { disabled: true } };
