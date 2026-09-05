"""Capture the pages a person sees while signing in.

These come from the demo stack, so they show the providers the demo configures
and agree with {doc}`/tutorials/federation-demo`.
"""

from .conftest import IDP
from .conftest import RP

import pytest


def test_login_page_options(anonymous_page, shot) -> None:
    """The sign-in options: one button per shown provider, and a password link.

    This is the first step of the login page, not the password form behind it.
    The password form is one click further in, and capturing that instead shows
    a page with no providers on it -- which is the opposite of what the page
    referencing this image is about.
    """
    anonymous_page.goto(f"{IDP}/login")
    anonymous_page.wait_for_selector("button:has-text('Sign in with a password')")
    # The provider buttons are the subject; assert one is there before capturing.
    anonymous_page.wait_for_selector("button:has-text('GitHub')")
    shot.capture("login-page-options")


def test_login_card(anonymous_page, shot) -> None:
    """The sign-in card alone, cropped, for the landing page.

    The same page as :func:`test_login_page_options`, framed to the card. A
    landing page wants the thing itself rather than a browser window that is
    four fifths empty, and cropping in the capture keeps that decision here
    rather than in whatever renders the Markdown.
    """
    anonymous_page.goto(f"{IDP}/login")
    anonymous_page.wait_for_selector("button:has-text('Sign in with a password')")
    anonymous_page.wait_for_selector("button:has-text('GitHub')")
    shot.capture("login-card", element=anonymous_page.locator(".loginForm"))


@pytest.mark.site(RP)
def test_identities_page(page_as_admin, shot) -> None:
    """A person's own sign-in methods."""
    page_as_admin.goto(f"{RP}/identities")
    page_as_admin.wait_for_load_state("networkidle")
    shot.capture("identities-page")
