/**
 * The sign-in block: the ways in for a visitor, a welcome for a user.
 *
 * Decided in the browser only. The page around the block may be rendered on
 * the server and cached, and what it says to somebody signed in is theirs --
 * so the server renders the block empty, for everybody, and the browser fills
 * it in.
 * @module components/Blocks/SignIn/View
 */
import React from 'react';
import { useSelector } from 'react-redux';
import type { BlocksFormData } from '@plone/types';
import { useClient } from '@plone/volto/hooks/client/useClient';

import LoginCard from '../../Login/LoginCard';
import LoginForm from '../../Login/LoginForm';
import { useLogin } from '../../Login/useLogin';
import type { SignInBlockData } from '../../../types';
import Welcome from '../../Welcome/Welcome';

/** What pressing anything does in a preview: nothing. */
const INERT = {
  onSelectProvider: () => {},
  onSendMagicLink: () => {},
  onPasswordLogin: () => {},
};

interface SignInOptionsProps {
  /** Whether this is an editor's preview, where nothing may be started. */
  preview?: boolean;
}

/**
 * The ways in, in the card `/login` shows them in.
 *
 * The card and not the page: `LoginPanel` also sets the document title and
 * claims `#page-login`, and neither is a block's to take.
 *
 * Never straight to a sole provider. Somebody on `/login` asked to sign in;
 * somebody on a page with this block came for the page.
 */
export const SignInOptions: React.FC<SignInOptionsProps> = ({
  preview = false,
}) => {
  const { form, title, description } = useLogin();
  return (
    <LoginCard title={title} description={description}>
      <LoginForm
        {...form}
        {...(preview ? INERT : {})}
        redirectToSoleProvider={false}
      />
    </LoginCard>
  );
};

interface ViewProps {
  /** The block's settings, as Volto hands any block its data. */
  data: BlocksFormData;
  className?: string;
  /** Set by the block's edit component, which renders this. */
  isEditMode?: boolean;
}

const View: React.FC<ViewProps> = ({ data, className, isEditMode }) => {
  const isClient = useClient();
  const token = useSelector((state: any) => state.userSession?.token);
  const block = data as SignInBlockData;
  // The editor is always signed in, so without this an editor could never
  // see the half of the block most visitors get.
  const preview = Boolean(isEditMode && block.previewAnonymous);

  let body: React.ReactNode = null;
  if (isClient) {
    body =
      token && !preview ? (
        <Welcome data={block} />
      ) : (
        <SignInOptions preview={preview} />
      );
  }

  return (
    <div
      className={['block', 'identity-sign-in', className]
        .filter(Boolean)
        .join(' ')}
    >
      {body}
    </div>
  );
};

export default View;
