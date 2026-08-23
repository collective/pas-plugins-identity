/**
 * The chrome around the login page.
 *
 * The panel, its markup and its classes are taken from `volto-authomatic`,
 * which is the shape Volto's own login page has: a fixed-width card with a
 * titled header, a description strip, and the form below. Two add-ons that
 * both replace `/login` looking like two different products is a worse
 * outcome than either of them looking like itself.
 * @module components/Login/LoginPanel
 */
import React from 'react';
import type { ReactNode } from 'react';
import { Container } from '@plone/components';
import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

interface LoginPanelProps {
  /** Heading, and the browser title. */
  title: string;
  /** The strip under the heading, saying what the options below are. */
  description: string;
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
      <Container className="wrapper">
        <Container className="title">{title}</Container>
        <Container className="description">{description}</Container>
        <Container className="form">{children}</Container>
      </Container>
    </Container>
  </div>
);

export default LoginPanel;
