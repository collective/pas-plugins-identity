/**
 * Vocabularies this add-on reads.
 * @module constants/vocabularies
 */

/**
 * The member fields a provider claim can be written to.
 *
 * Served by the backend from the site's live user schema, so it follows
 * whatever the **User Schema** control panel was used to add.
 */
export const USER_FIELDS_VOCABULARY = 'pas.plugins.identity.UserFields';

/**
 * The groups a provider's group can be mapped onto.
 *
 * Every group PAS knows, whichever plugin answers for it, minus the virtual
 * ones nobody is explicitly a member of.
 */
export const GROUPS_VOCABULARY = 'pas.plugins.identity.Groups';
