import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import OrderedObjectListWidget from './OrderedObjectListWidget';
import type { OrderedObjectListWidgetProps } from './OrderedObjectListWidget';
import {
  SOCIAL_LINK_SCHEMA,
  SOCIAL_LINKS,
  withStore,
} from '../../../stories/fixtures';

const meta: Meta<typeof OrderedObjectListWidget> = {
  title: 'Identity/Widgets/OrderedObjectListWidget',
  component: OrderedObjectListWidget,
  args: {
    id: 'social_links',
    title: 'Profiles',
    value: SOCIAL_LINKS,
    schema: SOCIAL_LINK_SCHEMA,
    onChange: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof OrderedObjectListWidget>;

/**
 * Give the story a store: Volto's dialog and widgets read from one. Dragging
 * needs nothing loaded, since react-aria ships with the add-on.
 */
const withAStore = withStore({});

/**
 * Render a widget that keeps the value it reports.
 *
 * @param Widget The widget.
 * @returns A story's render function.
 */
const keeping = (Widget: React.FC<OrderedObjectListWidgetProps>) =>
  function Render(args: OrderedObjectListWidgetProps) {
    const [value, setValue] = useState(args.value);
    return (
      <Widget
        {...args}
        value={value}
        onChange={(_id, next) => setValue(next)}
      />
    );
  };

/** Every field of the entry as a column, which is the default. */
export const Default: Story = {
  decorators: [withAStore],
  render: keeping(OrderedObjectListWidget),
};

/** The columns a backend picked with `widgetProps`. */
export const PickedColumns: Story = {
  ...Default,
  args: { columns: ['title', 'href'] },
};
