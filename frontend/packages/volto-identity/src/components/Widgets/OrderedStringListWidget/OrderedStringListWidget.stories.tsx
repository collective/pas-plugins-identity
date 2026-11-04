import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import OrderedStringListWidget from './OrderedStringListWidget';
import {
  EMAIL_ITEMS,
  PROFILE_EMAILS,
  withStore,
} from '../../../stories/fixtures';

const meta: Meta<typeof OrderedStringListWidget> = {
  title: 'Identity/Widgets/OrderedStringListWidget',
  component: OrderedStringListWidget,
  args: {
    id: 'emails',
    title: 'Email addresses',
    description: 'The addresses this person uses, most preferred first.',
    value: PROFILE_EMAILS.map((email) => email.address),
    items: EMAIL_ITEMS,
    uniqueItems: true,
    onChange: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof OrderedStringListWidget>;

/**
 * Give the story a store: Volto's dialog and widgets read from one. Dragging
 * needs nothing loaded, since react-aria ships with the add-on.
 */
const withAStore = withStore({});

/**
 * A Profile's addresses. The dialog asks with Volto's email widget, because
 * the value type is an `Email`, and refuses an address already listed.
 */
export const Default: Story = {
  decorators: [withAStore],
  render: function Render(args) {
    const [value, setValue] = useState(args.value);
    return (
      <OrderedStringListWidget
        {...args}
        value={value}
        onChange={(_id, next) => setValue(next)}
      />
    );
  },
};

/** No addresses yet, on a field that requires one. */
export const Required: Story = {
  ...Default,
  args: {
    value: [],
    required: true,
    error: ['Required input is missing.'],
  },
};
