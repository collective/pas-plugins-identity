/**
 * The chrome around the login page.
 *
 * The panel, its markup and its classes are taken from `volto-authomatic`,
 * which is the shape Volto's own login page has: a fixed-width card with a
 * titled header, a description strip, and the form below. Two add-ons that
 * both replace `/login` looking like two different products is a worse
 * outcome than either of them looking like itself.
 *
 * The card and its heading additionally wear the add-on's own `identity-surface`
 * classes, so this panel and the control panel's sections are the same card
 * described once.
 *
 * Every string it renders is a prop: the container decides what the page is
 * called and what it says, because that depends on what is actually below.
 * @module components/Login/LoginPanel
 */
import React from 'react';
import type { ReactNode } from 'react';
import { Container } from '@plone/components';
import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import './LoginPanel.scss';

interface LoginPanelProps {
  /** Heading, and the browser title. */
  title: string;
  /**
   * The strip under the heading, saying what the options below are.
   *
   * Optional: the callback and the first-login wait use this same card, and
   * neither has anything to say there. An empty strip is still a coloured
   * band with padding, so it is left out rather than rendered blank.
   */
  description?: string;
  children: ReactNode;
}

const LoginPanel: React.FC<LoginPanelProps> = ({
  title,
  description,
  children,
}) => (
  <div id="page-login">
    <Helmet title={title} />
    <Container className="loginForm">
      <Container className="wrapper identity-surface">
        <Container className="title identity-surface__header">
          {title}
        </Container>
        {description ? (
          <Container className="description">{description}</Container>
        ) : null}
        <Container className="form">{children}</Container>
      </Container>
    </Container>
  </div>
);

export default LoginPanel;
