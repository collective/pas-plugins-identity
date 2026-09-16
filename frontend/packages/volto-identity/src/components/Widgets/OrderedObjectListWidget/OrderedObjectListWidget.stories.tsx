import React, { useState } from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import OrderedObjectListWidget from './OrderedObjectListWidget';
import type { OrderedObjectListWidgetProps } from './OrderedObjectListWidget';
import { DND_LIBRARIES } from '../../ControlPanel/ProvidersTable';
import {
  loadLazyLibraries,
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

/** Put the loaded drag library in the store; see `ProvidersTable.stories`. */
const withDragging = (
  Story: () => ReactNode,
  { loaded }: { loaded: Record<string, any> },
) => withStore({ lazyLibraries: loaded.lazyLibraries })(Story);

const loadDragging = async () => ({
  lazyLibraries: await loadLazyLibraries(DND_LIBRARIES),
});

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
  loaders: [loadDragging],
  decorators: [withDragging],
  render: keeping(OrderedObjectListWidget),
};

/** The columns a backend picked with `widgetProps`. */
export const PickedColumns: Story = {
  ...Default,
  args: { columns: ['title', 'href'] },
};
