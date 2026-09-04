import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import IdentitiesMenuItem from './IdentitiesMenuItem';
import { withPersonalTools } from '../../storybook/withUserMenu';

const meta: Meta<typeof IdentitiesMenuItem> = {
  title: 'Identity/UserMenu/IdentitiesMenuItem',
  component: IdentitiesMenuItem,
  decorators: [withPersonalTools],
  parameters: { fullBleed: true },
};
export default meta;

type Story = StoryObj<typeof IdentitiesMenuItem>;

/**
 * The plug renders nothing on its own -- it registers a renderer -- so the
 * story has to include the pluggable that consumes it, the way Volto's user
 * menu does.
 */
export const InTheUserMenu: Story = {
  render: () => (
    <PluggablesProvider>
      <IdentitiesMenuItem />
      <ul>
        <Pluggable name="toolbar-user-menu" />
      </ul>
    </PluggablesProvider>
  ),
};
