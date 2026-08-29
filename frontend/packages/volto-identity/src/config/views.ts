import type { ConfigType } from '@plone/registry';
import GroupView from '../components/Views/GroupView';
import ProfileView from '../components/Views/ProfileView';

/** Portal type of a user's Profile. */
export const PROFILE_TYPE = 'UserProfile';

/** Portal type of a group. */
export const GROUP_TYPE = 'UserGroup';

/**
 * Give the two principal types views of their own.
 *
 * Both are content, so without this they rendered through Volto's default
 * view: a title and a body that is empty, because neither type has rich text.
 * What each page has to say is on fields the default view does not know about
 * -- a person's picture, a group's nesting -- and for a group most of it is
 * not on the content object at all.
 *
 * Registered by portal type rather than as a layout, so a site that files its
 * users under its own type keeps its own view and gets neither of these.
 */
export default function install(config: ConfigType) {
  config.views.contentTypesViews = {
    ...config.views.contentTypesViews,
    [PROFILE_TYPE]: ProfileView,
    [GROUP_TYPE]: GroupView,
  };
  return config;
}
