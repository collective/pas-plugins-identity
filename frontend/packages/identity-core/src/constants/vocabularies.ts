/**
 * Vocabularies this add-on reads.
 * @module constants/vocabularies
 */

/**
 * The Profile fields a provider claim can be written to.
 *
 * Four of them, and the backend decides which: a login writes a full name, a
 * home page, a biography and a location, and nothing else. An address and a
 * portrait both arrive on a login without being mapped, which is why neither
 * is here.
 *
 * The form does not build the vocabulary's URL from this name -- the served
 * schema carries it -- so this is what the fixtures and the tests address it
 * by.
 */
export const USER_FIELDS_VOCABULARY = 'pas.plugins.identity.UserFields';

/**
 * The groups a provider's group can be mapped onto.
 *
 * Every group PAS knows, whichever plugin answers for it, minus the virtual
 * ones nobody is explicitly a member of.
 */
export const GROUPS_VOCABULARY = 'pas.plugins.identity.Groups';
