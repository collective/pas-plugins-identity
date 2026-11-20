import type { Meta, StoryObj } from '@storybook/react';

import Edit from './Edit';
import { LOADED, OPTIONS, withStore } from '../../../stories/fixtures';

const meta: Meta<typeof Edit> = {
  title: 'Identity/Blocks/SignIn/Edit',
  component: Edit,
  decorators: [
    withStore({
      loginOptions: { ...LOADED, data: OPTIONS },
      providerLogin: {},
      magicLinkSend: {},
      userSession: { token: null, login: {} },
    }),
  ],
};
export default meta;

type Story = StoryObj<typeof Edit>;

/**
 * The block in the editor with the preview switched on.
 *
 * Pressing anything does nothing: an editor checking how the block looks is
 * not signing in. The sidebar is rendered into the editor's own portal, so
 * it has nowhere to appear here.
 */
export const PreviewingTheSignInOptions: Story = {
  args: {
    data: { '@type': 'identitySignIn', previewAnonymous: true },
    block: 'sign-in',
    selected: false,
    onChangeBlock: () => {},
  } as any,
};
