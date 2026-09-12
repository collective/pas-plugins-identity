/**
 * The login card as a page of its own.
 *
 * `LoginCard` is the card. This is what makes it a page: the document title,
 * and `#page-login`, which Volto's theme centres the page by.
 *
 * Every string it renders is a prop: the container decides what the page is
 * called and what it says, because that depends on what is actually below.
 * @module components/Login/LoginPanel
 */
import React from 'react';
import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import LoginCard from './LoginCard';
import type { LoginCardProps } from './LoginCard';

/** The card's props. Its `title` is the browser title as well. */
type LoginPanelProps = LoginCardProps;

const LoginPanel: React.FC<LoginPanelProps> = ({
  title,
  description,
  children,
}) => (
  <div id="page-login">
    <Helmet title={title} />
    <LoginCard title={title} description={description}>
      {children}
    </LoginCard>
  </div>
);

export default LoginPanel;
