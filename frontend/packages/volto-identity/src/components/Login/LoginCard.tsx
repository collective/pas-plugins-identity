/**
 * The login card, without a page around it.
 *
 * The card, its markup and its classes are taken from `volto-authomatic`,
 * which is the shape Volto's own login page has: a fixed-width card with a
 * titled header, a description strip, and the form below. Two add-ons that
 * both replace `/login` looking like two different products is a worse
 * outcome than either of them looking like itself.
 *
 * The login page puts the card on a page of its own through `LoginPanel`. The
 * sign-in block puts it on whatever page the block is on, which is why this
 * sets no document title and claims no page id.
 *
 * The card and its heading additionally wear the add-on's own
 * `identity-surface` classes, so this card and the control panel's sections
 * are the same card described once.
 * @module components/Login/LoginCard
 */
import React from 'react';
import type { ReactNode } from 'react';
import { Container } from '@plone/components';

import './LoginCard.scss';

export interface LoginCardProps {
  /** The heading. */
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

const LoginCard: React.FC<LoginCardProps> = ({
  title,
  description,
  children,
}) => (
  <Container className="loginForm identity-login-card">
    <Container className="wrapper identity-surface">
      <Container className="title identity-surface__header">{title}</Container>
      {description ? (
        <Container className="description">{description}</Container>
      ) : null}
      <Container className="form">{children}</Container>
    </Container>
  </Container>
);

export default LoginCard;
