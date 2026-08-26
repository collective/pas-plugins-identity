/**
 * The personal-tools menu, rewritten.
 *
 * Takes Volto's place through
 * `customizations/volto/components/manage/Toolbar/PersonalTools`, which is
 * where the reason for shadowing it is written down.
 *
 * **Not** a verbatim copy of `@plone/volto/components/manage/Toolbar/PersonalTools`
 * (Volto 19.3.0) with a patch: it is a rewrite in TypeScript that keeps the
 * markup, the class names and the behaviour Volto's stylesheet and tests
 * expect, and changes what was worth changing. On a Volto upgrade, read
 * upstream's diff for *behavioural* changes and port those -- a literal file
 * diff will not be meaningful.
 *
 * WHAT DIFFERS FROM UPSTREAM, and why:
 *
 * - **The menu list is nothing but the pluggable.** Upstream writes Profile,
 *   Preferences and Site Setup into the list and puts `toolbar-user-menu`
 *   after them, so an add-on can only append: wanting an entry *between* two
 *   of Volto's, or wanting one of them gone, meant shadowing this component
 *   again. All three are plugs now -- see
 *   `components/UserMenu/UserMenuPlugs` -- so the menu is one ordered list a
 *   site composes. `loadComponent` reaches the Preferences entry through the
 *   pluggable's `params`, which is what that mechanism is for.
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
 *   `id="toolbar-profile"` in the plug that now renders it, matching the
 *   `toolbar-logout` in the header here, which upstream already spells that
 *   way.
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
 * @module components/Toolbar/PersonalTools
 */
import React from 'react';
import type { RefObject } from 'react';
import { useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import { useIntl, defineMessages } from 'react-intl';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import { Pluggable } from '@plone/volto/components/manage/Pluggable';
import { getBaseUrl } from '@plone/volto/helpers/Url/Url';
import logoutSVG from '@plone/volto/icons/log-out.svg';
import backSVG from '@plone/volto/icons/back.svg';

const messages = defineMessages({
  back: { id: 'Back', defaultMessage: 'Back' },
  logout: { id: 'Logout', defaultMessage: 'Logout' },
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
  // Memoized because `Pluggable` memoizes its render on the params object: a
  // fresh one every render would rebuild every entry on every render.
  const pluggableParams = React.useMemo(
    () => ({ loadComponent }),
    [loadComponent],
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
          <Pluggable name="toolbar-user-menu" params={pluggableParams} />
        </ul>
      </div>
    </div>
  );
};

export default PersonalTools;
