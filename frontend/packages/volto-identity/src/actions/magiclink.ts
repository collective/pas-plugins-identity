/**
 * Actions for the emailed single-use sign-in link.
 * @module actions/magiclink
 */

import { CONFIRM_MAGIC_LINK, SEND_MAGIC_LINK } from '../constants/ActionTypes';
import { endpoints } from '@plone-collective/identity-core';

/**
 * Ask for a magic link.
 *
 * @param email Address to send it to.
 */
export function sendMagicLink(email: string) {
  return {
    type: SEND_MAGIC_LINK,
    request: { op: 'post', path: endpoints.magicLink(), data: { email } },
  };
}

/**
 * Redeem a magic link.
 *
 * @param token The token from the emailed link.
 */
export function confirmMagicLink(token: string) {
  return {
    type: CONFIRM_MAGIC_LINK,
    request: {
      op: 'post',
      path: endpoints.magicLinkConfirm(),
      data: { token },
    },
  };
}
