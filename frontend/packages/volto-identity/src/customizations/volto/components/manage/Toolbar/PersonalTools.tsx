/**
 * The personal-tools menu, rewritten.
 *
 * Shadows `@plone/volto/components/manage/Toolbar/PersonalTools` (Volto
 * 19.3.0). This is **not** a verbatim copy with a patch: it is a rewrite in
 * TypeScript that keeps the markup, the class names and the behaviour Volto's
 * stylesheet and tests expect, and changes what was worth changing. On a Volto
 * upgrade, read upstream's diff for *behavioural* changes and port those --
 * a literal file diff will not be meaningful.
 *
 * WHY IT IS SHADOWED. Volto has no extension point here. The only pluggable
 * is `toolbar-user-menu`, at the end of the menu *list*, so the avatar block
 * above it cannot be touched without replacing this component.
 *
 * WHAT DIFFERS FROM UPSTREAM, and why:
 *
 * - **The avatar block is gone.** It drew a 96px portrait, or a camera icon
 *   for the many users who have never uploaded one -- the same picture for
 *   everybody, saying "no image here" rather than "this is you". Who is
 *   signed in is shown by `<UserAvatar>` on the toolbar button that opens
 *   this menu, where it is visible without opening anything.
 *
 * - **The Profile link has a stable id.** Upstream sets
 *   `id={intl.formatMessage(messages.profile)}`, so the DOM id is the
 *   *translated* label: `id="Profile"` in English, `id="Perfil"` in
 *   Portuguese. Anything keying on it -- a test, a stylesheet, an
 *   integration -- works in one language and silently not in the next. It is
 *   `id="toolbar-profile"` here, matching `toolbar-logout` two lines below
 *   it, which upstream already spells that way.
 *
 * - **It does not fetch the user.** Upstream decodes the JWT and dispatches
 *   `getUser` on mount. This add-on already holds the signed-in user, loaded
 *   once per userid by `UserProfileLoader` from the same `@users/<userid>`
 *   endpoint, so fetching again on every menu open is a duplicate request for
 *   data already in the store. `jwt-decode` goes with it.
 *
 * - **The back button and the logout link have accessible names.** Both were
 *   an `<Icon>` with a `title` inside an element with no label of its own, so
 *   a screen reader announced them as an unnamed button and an unnamed link.
 *   The Preferences button beside them already carried an `aria-label`; these
 *   two now do too.
 *
 * - **No `classnames`.** Upstream uses it for one conditional class. It is
 *   Volto's dependency rather than this package's, and this add-on declares
 *   no runtime dependencies at all -- so the one class is joined by hand.
 *
 * - **Dead code is gone.** `const [, setPushed] = useState(false)` -- the
 *   value was never read, so the only effect of setting it was a re-render
 *   per menu push. The commented-out `<Stats />` and the "should be a
 *   Component by itself" note went too.
 *
 * @module customizations/volto/components/manage/Toolbar/PersonalTools
 */
import React from 'react';
import type { RefObject } from 'react';
import { useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import { FormattedMessage, useIntl, defineMessages } from 'react-intl';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import { Pluggable } from '@plone/volto/components/manage/Pluggable';
import { getBaseUrl } from '@plone/volto/helpers/Url/Url';
import logoutSVG from '@plone/volto/icons/log-out.svg';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';
import backSVG from '@plone/volto/icons/back.svg';

const messages = defineMessages({
  back: { id: 'Back', defaultMessage: 'Back' },
  logout: { id: 'Logout', defaultMessage: 'Logout' },
  preferences: { id: 'Preferences', defaultMessage: 'Preferences' },
  profile: { id: 'Profile', defaultMessage: 'Profile' },
});

export interface PersonalToolsProps {
  /** Slide another panel into the toolbar, by its registered name. */
  loadComponent: (selector: string) => void;
  /** Slide this panel back out. */
  unloadComponent: () => void;
  /** The toolbar element, read for the width this panel matches. */
  theToolbar: RefObject<HTMLElement | null>;
  /** Whether the toolbar is showing content actions beside this menu. */
  hasActions?: boolean;
}

/**
 * The name to show for the signed-in user.
 *
 * Never empty: a header with nothing in it reads as a broken menu rather
 * than as a user who has not filled their name in.
 *
 * @param user The user held in the store, if loaded.
 * @returns The full name, the login name, or the userid.
 */
function displayName(user: {
  fullname?: string | null;
  username?: string | null;
  id?: string | null;
}): string {
  return user?.fullname || user?.username || user?.id || '';
}

const PersonalTools: React.FC<PersonalToolsProps> = ({
  loadComponent,
  unloadComponent,
  theToolbar,
  hasActions,
}) => {
  const intl = useIntl();
  const { pathname } = useLocation();
  const user = useSelector((state: any) => state.userProfile?.data) ?? {};
  const siteSetupAction = useSelector((state: any) =>
    state.actions?.actions?.user?.find(
      (action: { id?: string }) => action?.id === 'plone_setup',
    ),
  );

  return (
    <div
      className={
        hasActions
          ? 'personal-tools pastanaga-menu has-inner-actions'
          : 'personal-tools pastanaga-menu'
      }
      style={{
        // Read during render, as upstream does. The panel slides in over the
        // toolbar and has to be exactly its width; a layout effect would
        // size it one frame late, which is visible as a jump.
        flex: theToolbar?.current
          ? `0 0 ${theToolbar.current.getBoundingClientRect().width}px`
          : undefined,
      }}
    >
      <header className="header">
        <button
          className="back"
          aria-label={intl.formatMessage(messages.back)}
          onClick={unloadComponent}
        >
          <Icon
            name={backSVG}
            size="30px"
            title={intl.formatMessage(messages.back)}
          />
        </button>
        <div className="vertical divider" />
        <h2>{displayName(user)}</h2>
        <Link
          id="toolbar-logout"
          aria-label={intl.formatMessage(messages.logout)}
          to={`${getBaseUrl(pathname)}/logout`}
        >
          <Icon
            className="logout"
            name={logoutSVG}
            size="30px"
            title={intl.formatMessage(messages.logout)}
          />
        </Link>
      </header>
      <div className="pastanaga-menu-list">
        <ul>
          <li>
            <Link id="toolbar-profile" to="/personal-information">
              <FormattedMessage id="Profile" defaultMessage="Profile" />
              <Icon name={rightArrowSVG} size="24px" />
            </Link>
          </li>
          <li>
            <button
              id="toolbar-preferences"
              aria-label={intl.formatMessage(messages.preferences)}
              onClick={() => loadComponent('preferences')}
            >
              <FormattedMessage id="Preferences" defaultMessage="Preferences" />
              <Icon name={rightArrowSVG} size="24px" />
            </button>
          </li>
          {siteSetupAction && (
            <li>
              <Link id="toolbar-site-setup" to="/controlpanel">
                <FormattedMessage id="Site Setup" defaultMessage="Site Setup" />
                <Icon name={rightArrowSVG} size="24px" />
              </Link>
            </li>
          )}
          <Pluggable name="toolbar-user-menu" />
        </ul>
      </div>
    </div>
  );
};

export default PersonalTools;
