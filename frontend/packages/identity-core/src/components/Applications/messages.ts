/**
 * What a page around `ApplicationsPanel` says.
 *
 * The panel draws the list; the page that renders it asks before a
 * withdrawal and reports the outcome. The Volto add-on's page says these
 * itself, in react-intl; a frontend translating through core's catalogues
 * takes them from here.
 * @module components/Applications/messages
 */
import { defineMessages } from '#i18n';

export const applicationsMessages = defineMessages({
  title: { id: 'Applications', defaultMessage: 'Applications' },
  confirm: {
    id: 'Withdraw access for {client}?',
    defaultMessage:
      'Withdraw access for {client}? It will be signed out everywhere and ' +
      'will have to ask you again next time.',
  },
  withdraw: { id: 'Withdraw access', defaultMessage: 'Withdraw access' },
  withdrawn: { id: 'Access withdrawn', defaultMessage: 'Access withdrawn' },
  failed: {
    id: 'That did not work. Please try again.',
    defaultMessage: 'That did not work. Please try again.',
  },
});
