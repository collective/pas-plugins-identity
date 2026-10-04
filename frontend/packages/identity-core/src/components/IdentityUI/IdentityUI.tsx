/**
 * What a frontend lends this package's components.
 *
 * The components here know what to draw, but not how this frontend
 * translates, links or draws an icon. Each frontend's add-on wraps them in an
 * `IdentityUIProvider` that answers those questions, and names the
 * frontend's own pages the components link to. Without one, the
 * components still work: in English, with plain links and plain icons.
 * @module components/IdentityUI
 */
import React, { createContext, useContext } from 'react';
import type { ComponentType, ReactNode } from 'react';

import { translateDefault } from '#i18n';
import type { Translate } from '#i18n';

/** A link to a path inside the site. */
export interface IdentityLinkProps {
  /** The path, beginning with a slash. */
  href: string;
  className?: string;
  children?: ReactNode;
}

/** The icons the components draw. */
export interface IdentityIcons {
  /** On a submit button: go ahead. */
  submit: ReactNode;
  /** On a clear button: empty the form. */
  clear: ReactNode;
  /** On a way back to a list. */
  back: ReactNode;
  /** On a button that opens one item's details. */
  details: ReactNode;
  /** On a button that removes or withdraws something. */
  remove: ReactNode;
}

/** The frontend's own pages the components link to. */
export interface IdentityPaths {
  /** Where a visitor who forgot their password asks for a new one. */
  passwordReset: string;
}

/** What a frontend lends the components. */
export interface IdentityUI {
  /** Turn a message into text in the reader's language. */
  t: Translate;
  /**
   * Link within the site without reloading it.
   *
   * A plain anchor would throw the running application away.
   */
  Link: ComponentType<IdentityLinkProps>;
  icons: IdentityIcons;
  paths: IdentityPaths;
  /**
   * The reader's language, as a BCP 47 tag.
   *
   * For what the components format themselves: dates, and the plural forms
   * of a message.
   */
  locale: string;
}

/**
 * A plain anchor.
 *
 * @param props The link.
 * @returns The anchor.
 */
const PlainLink: ComponentType<IdentityLinkProps> = ({
  href,
  className,
  children,
}) => (
  <a href={href} className={className}>
    {children}
  </a>
);

/**
 * Draw a simple stroked icon.
 *
 * @param path The SVG path.
 * @returns The icon.
 */
function strokeIcon(path: string): ReactNode {
  return (
    <svg
      className="circled"
      width="30"
      height="30"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
      focusable="false"
    >
      <path d={path} />
    </svg>
  );
}

/** What the components use when no frontend has provided anything. */
export const defaultIdentityUI: IdentityUI = {
  t: translateDefault,
  Link: PlainLink,
  icons: {
    submit: strokeIcon('M5 12h14M13 6l6 6-6 6'),
    clear: strokeIcon('M6 6l12 12M18 6L6 18'),
    back: strokeIcon('M19 12H5M11 18l-6-6 6-6'),
    details: strokeIcon('M9 6l6 6-6 6'),
    remove: strokeIcon('M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13'),
  },
  // Volto's, which was the only frontend when these were written.
  paths: {
    passwordReset: '/passwordreset',
  },
  locale: 'en',
};

const IdentityUIContext = createContext<IdentityUI>(defaultIdentityUI);

/**
 * Lend the components inside what this frontend provides.
 *
 * Anything left out keeps its default, so a frontend overrides only what it
 * has: `icons` and `paths` may be given in part, too.
 *
 * @param props What to lend, and the components to lend it to.
 * @returns The provider.
 */
export function IdentityUIProvider({
  t,
  Link,
  icons,
  paths,
  locale,
  children,
}: Partial<Omit<IdentityUI, 'icons' | 'paths'>> & {
  icons?: Partial<IdentityIcons>;
  paths?: Partial<IdentityPaths>;
  children?: ReactNode;
}) {
  const value: IdentityUI = {
    t: t ?? defaultIdentityUI.t,
    Link: Link ?? defaultIdentityUI.Link,
    icons: { ...defaultIdentityUI.icons, ...icons },
    paths: { ...defaultIdentityUI.paths, ...paths },
    locale: locale ?? defaultIdentityUI.locale,
  };
  return (
    <IdentityUIContext.Provider value={value}>
      {children}
    </IdentityUIContext.Provider>
  );
}

/**
 * Read what the frontend lent.
 *
 * @returns The translate function, the link component, the icons and the
 *   paths.
 */
export function useIdentityUI(): IdentityUI {
  return useContext(IdentityUIContext);
}
