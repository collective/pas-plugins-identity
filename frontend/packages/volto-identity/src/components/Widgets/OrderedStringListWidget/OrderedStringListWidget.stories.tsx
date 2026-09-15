import React, { useState } from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import OrderedStringListWidget from './OrderedStringListWidget';
import { DND_LIBRARIES } from '../../ControlPanel/ProvidersTable';
import {
  EMAIL_ITEMS,
  loadLazyLibraries,
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

/** Put the loaded drag library in the store; see `ProvidersTable.stories`. */
const withDragging = (
  Story: () => ReactNode,
  { loaded }: { loaded: Record<string, any> },
) => withStore({ lazyLibraries: loaded.lazyLibraries })(Story);

const loadDragging = async () => ({
  lazyLibraries: await loadLazyLibraries(DND_LIBRARIES),
});

/**
 * A Profile's addresses. The dialog asks with Volto's email widget, because
 * the value type is an `Email`, and refuses an address already listed.
 */
export const Default: Story = {
  loaders: [loadDragging],
  decorators: [withDragging],
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
