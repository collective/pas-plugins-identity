/**
 * The sign-in block's id, its sidebar, and its default welcome message.
 * @module components/Blocks/SignIn/schema
 */
import { defineMessages } from 'react-intl';
import type { IntlShape } from 'react-intl';

export const messages = defineMessages({
  title: { id: 'Sign-in', defaultMessage: 'Sign-in' },
  default: { id: 'Default', defaultMessage: 'Default' },
  editing: { id: 'Editing', defaultMessage: 'Editing' },
  greeting: { id: 'Welcome message', defaultMessage: 'Welcome message' },
  greetingDescription: {
    id: 'Plain text. {username} is the name the user signs in with, and {fullname} their full name.',
    defaultMessage:
      'Plain text. {username} is the name the user signs in with, and {fullname} their full name.',
  },
  defaultGreeting: {
    id: 'Hello {fullname}!',
    defaultMessage: 'Hello {fullname}!',
  },
  showProfile: {
    id: 'Link to their profile',
    defaultMessage: 'Link to their profile',
  },
  showEmail: {
    id: 'Their preferred email',
    defaultMessage: 'Their preferred email',
  },
  showProvider: {
    id: 'What they signed in with',
    defaultMessage: 'What they signed in with',
  },
  showLastLogin: {
    id: 'When they last signed in',
    defaultMessage: 'When they last signed in',
  },
  previewAnonymous: {
    id: 'Preview the sign-in options',
    defaultMessage: 'Preview the sign-in options',
  },
  previewAnonymousDescription: {
    id: 'While editing only: show what a visitor who is not signed in sees.',
    defaultMessage:
      'While editing only: show what a visitor who is not signed in sees.',
  },
});

/**
 * The placeholders, given themselves as values.
 *
 * To `react-intl`, the `{fullname}` in a message is an argument. Formatted
 * with no value for it, react-intl 3.12 reports an error through `onError`
 * -- two or three per call -- and then falls back to the message source,
 * braces and all. Given itself as the value, it formats without complaint
 * into that same text, which is what a translator keeps and an editor needs
 * to see.
 */
const AS_TYPED = { username: '{username}', fullname: '{fullname}' };

/**
 * The welcome message a block has until an editor writes one.
 *
 * @param intl The current `react-intl` instance.
 * @returns The translated default, placeholders still in it.
 */
export function defaultGreeting(intl: IntlShape): string {
  return intl.formatMessage(messages.defaultGreeting, AS_TYPED);
}

/**
 * Describe the block's sidebar.
 *
 * Also its `blockSchema`, which is how a new block gets its defaults. The
 * view does not rely on them being there: a block saved before a field
 * existed has no value for it, and every line reads a missing switch as on.
 *
 * @param args What Volto passes a block schema.
 * @param args.intl The current `react-intl` instance.
 * @returns The schema.
 */
export function signInBlockSchema({ intl }: { intl: IntlShape }) {
  return {
    title: intl.formatMessage(messages.title),
    fieldsets: [
      {
        id: 'default',
        title: intl.formatMessage(messages.default),
        fields: [
          'greeting',
          'showProfile',
          'showEmail',
          'showProvider',
          'showLastLogin',
        ],
      },
      {
        id: 'editing',
        title: intl.formatMessage(messages.editing),
        fields: ['previewAnonymous'],
      },
    ],
    properties: {
      greeting: {
        title: intl.formatMessage(messages.greeting),
        description: intl.formatMessage(messages.greetingDescription, AS_TYPED),
        default: defaultGreeting(intl),
      },
      showProfile: {
        type: 'boolean',
        title: intl.formatMessage(messages.showProfile),
        default: true,
      },
      showEmail: {
        type: 'boolean',
        title: intl.formatMessage(messages.showEmail),
        default: true,
      },
      showProvider: {
        type: 'boolean',
        title: intl.formatMessage(messages.showProvider),
        default: true,
      },
      showLastLogin: {
        type: 'boolean',
        title: intl.formatMessage(messages.showLastLogin),
        default: true,
      },
      previewAnonymous: {
        type: 'boolean',
        title: intl.formatMessage(messages.previewAnonymous),
        description: intl.formatMessage(messages.previewAnonymousDescription),
      },
    },
    required: [],
  };
}
