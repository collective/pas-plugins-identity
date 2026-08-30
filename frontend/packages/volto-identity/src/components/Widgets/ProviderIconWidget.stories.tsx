import type { Meta, StoryObj } from '@storybook/react';

import ProviderIconWidget from './ProviderIconWidget';

const SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">' +
  '<path d="M8 1l7 13H1z"/></svg>';

const meta: Meta<typeof ProviderIconWidget> = {
  title: 'Identity/Widgets/ProviderIconWidget',
  component: ProviderIconWidget,
  args: {
    id: 'icon',
    title: 'Icon',
    value: `filenameb64:${btoa('icon.svg')};datab64:${btoa(SVG)}`,
    onChange: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProviderIconWidget>;

/** An icon already uploaded, previewed as the button will draw it. */
export const WithIcon: Story = {};

/** No icon yet, which is how every provider starts. */
export const Empty: Story = { args: { value: '' } };

/** While something else is in flight. */
export const Disabled: Story = { args: { isDisabled: true } };
