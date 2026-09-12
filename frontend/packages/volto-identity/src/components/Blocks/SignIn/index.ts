import type { BlockConfigBase } from '@plone/types';
import userSVG from '@plone/volto/icons/user.svg';

import SignInEdit from './Edit';
import SignInView from './View';
import { signInBlockSchema } from './schema';

export const SIGN_IN_BLOCK = 'identitySignIn';

const IdentitySignInBlockInfo: BlockConfigBase = {
  id: SIGN_IN_BLOCK,
  title: 'Sign-in',
  icon: userSVG,
  group: 'common',
  view: SignInView,
  edit: SignInEdit,
  // `@plone/types` declares its own `IntlShape` and `JSONSchema`, which
  // `react-intl`'s and this schema's plain object do not match by name.
  blockSchema: signInBlockSchema as unknown as BlockConfigBase['blockSchema'],
  // Offered by no block chooser until a project says so. A page greeting
  // its reader by name is a decision about that site, not a default for
  // every site that installs sign-in.
  restricted: true,
  mostUsed: false,
  sidebarTab: 1,
};

export default IdentitySignInBlockInfo;
