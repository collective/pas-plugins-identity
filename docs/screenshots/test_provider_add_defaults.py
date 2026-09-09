"""What the add-provider form shows once Google is chosen as the driver.

A diagnostic rather than a documentation capture. The images go to a scratch
directory, not to ``docs/_static/screens/``, so nothing here can leave an orphan
in the repository and none of these names needs to appear in the Markdown.

**The question it answers.** ``ProviderConfig.__init__`` applies the driver's
defaults, so a provider saved from an empty form still stores Google's scope --
the values are not lost. What is in doubt is whether the operator can *see* them
before saving. ``IOAuth2Settings.scope`` declares ``default=()`` and
``@identity-drivers`` publishes ``default_propertymap`` and ``default_groupmap``
but no ``default_scope``, so the prediction is: property map filled in, scope box
empty.

The script asserts only what has to hold for the capture to be of the right
screen -- the form opened, Google is the selected driver, the tabs are the ones
the driver's fieldsets produce. What the fields *contain* is reported rather than
asserted, because that is the thing under investigation and an assertion here
would have to be inverted the day it is fixed.
"""

from .conftest import IDP
from pathlib import Path
from playwright.sync_api import Page

import json
import os
import pytest


#: Where the diagnostic images go: under the Sphinx build directory, which is
#: already ignored, and never into ``docs/_static/screens/``. These are evidence
#: for an issue rather than part of the built site, so none of these names has to
#: appear in the Markdown and none of them can become an orphan image.
OUT = Path(
    os.environ.get(
        "IDENTITY_DIAGNOSTIC_DIR",
        Path(__file__).resolve().parents[1] / "_build" / "diagnostics",
    )
)

#: The driver under investigation, as it appears in the dropdown.
DRIVER_TITLE = "Google"

#: Fields whose contents are the subject. Read off the form after the driver is
#: chosen, and printed rather than asserted.
#:
#: Each one has a driver default that differs from its schema default, so each
#: is a place where the form and the record about to be written can disagree.
WATCHED = (
    "config.scope",
    "config.userid_source",
    "config.trust_email_verification",
    "config.create_user",
    "config.auto_link_by_email",
    "propertymap",
    "groupmap",
)


def _stabilize(page: Page) -> None:
    """Quiet the page down before photographing it.

    The same three measures the documentation harness applies, minus the mask
    machinery it does not need here: no transitions, no blinking caret, and the
    network given a chance to settle.

    :param page: The page to steady.
    """
    page.add_style_tag(
        content=(
            "*, *::before, *::after {"
            "animation-duration: 0s !important;"
            "transition-duration: 0s !important;"
            "caret-color: transparent !important;"
            "}"
        )
    )
    page.mouse.move(0, 0)
    page.wait_for_load_state("networkidle", timeout=15_000)


def _shoot(page: Page, name: str, *, full_page: bool = False) -> Path:
    """Write one diagnostic image.

    :param page: The page to photograph.
    :param name: Filename, without extension.
    :param full_page: Photograph the whole document rather than the window, for
        a tab whose fields run past the fold.
    :returns: The path written.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{name}.png"
    _stabilize(page)
    page.screenshot(path=target, full_page=full_page)
    print(f"  wrote {target}")
    return target


def _field_value(page: Page, field_id: str) -> object:
    """Read what a Volto form field currently displays.

    Read from the rendered control rather than from the store, because the
    question is what the operator sees rather than what will be saved -- and on
    this form those two disagree, which is the whole point.

    Three widget shapes, taken in the order that avoids reading the wrong one.
    A ``react-select`` carries a hidden text input that is always empty, so
    asking for inputs first reports every choice and every scope as ``""``; its
    real value is the label element. A checkbox has no text at all and has to be
    asked whether it is checked.

    :param page: The page holding the form.
    :param field_id: The schema field name, as Volto ids it.
    :returns: The displayed value, or ``None`` when the field is not on screen.
    """
    # Volto ids a field wrapper `field-<name>`, and a config field's name
    # carries a dot -- which is a class separator in a CSS selector and has to
    # be escaped, or the query silently matches nothing.
    wrapper = page.locator(f"#field-{field_id.replace('.', chr(92) + '.')}")
    if not wrapper.count():
        # Not an error: a field lives on one tab, and Volto mounts only the
        # active one, so every field is absent from four captures out of five.
        return None

    chosen = wrapper.locator(
        ".react-select__single-value, .react-select__multi-value__label"
    )
    if chosen.count():
        return [chosen.nth(i).inner_text().strip() for i in range(chosen.count())]
    if wrapper.locator(".react-select__placeholder").count():
        return "(empty)"

    # For a checkbox Volto puts the id on the input itself rather than on a
    # wrapper around it, so the descendant search finds nothing and the read
    # falls through to an empty `inner_text` -- which reports every checkbox as
    # `""` whether it is ticked or not.
    boxes = wrapper.locator(
        "xpath=self::input[@type='checkbox'] | .//input[@type='checkbox']"
    )
    if boxes.count():
        return boxes.first.is_checked()

    values = wrapper.locator("input:not([type=hidden]):not([type=checkbox])")
    if values.count():
        return [values.nth(i).input_value() for i in range(values.count())]
    return (wrapper.inner_text() or "").strip()


@pytest.mark.site(IDP)
def test_add_provider_with_google_driver(page_as_admin: Page) -> None:
    """Open the add form, choose Google, and photograph every tab.

    Four things are proved before anything is photographed, because each of them
    has a silent failure mode: a click that lands on a table cell leaves the list
    on screen and captures it under the wrong name; a driver that was never
    selected leaves the form on its previous schema; and a form whose tabs have
    not rendered yet photographs a single flat column that looks like the defect
    under investigation but is only a race.
    """
    page = page_as_admin
    page.goto(f"{IDP}/controlpanel/identity-providers")
    page.wait_for_load_state("networkidle")
    _shoot(page, "01-providers-list")

    # The control is an icon button; its accessible name is the only stable
    # handle. Clicking the heading text hits a layout element and does nothing.
    page.get_by_label("Add provider").click()

    # Prove the form opened rather than trusting the click.
    page.wait_for_selector("#field-driver", timeout=15_000)
    _shoot(page, "02-add-form-no-driver")

    # react-select, with Volto's `react-select` class prefix. Clicking the
    # control opens the menu; the option is picked by its exact text so that
    # "Google" cannot match a driver merely containing the word.
    page.locator("#field-driver .react-select__control").click()
    page.locator(".react-select__option", has_text=DRIVER_TITLE).first.click()

    # Choosing a driver remounts the form under a new key, and the driver's own
    # fieldsets arrive as new tabs -- for Google, Settings and Accounts, taking
    # the row from three to five. Waiting on a *tab* rather than on a field is
    # what makes the remount observable: Volto mounts only the active tab, so
    # `#field-config.client_id` does not exist until Settings is opened, and
    # waiting for it times out on a form that selected the driver perfectly.
    page.wait_for_selector(".formtabs button:has-text('Settings')", timeout=15_000)

    selected = (
        page.locator("#field-driver .react-select__single-value").inner_text().strip()
    )
    assert selected == DRIVER_TITLE, (
        f"The driver box reads {selected!r}. Every capture below would be of "
        f"some other driver's form."
    )

    tabs = page.locator(".formtabs button")
    titles = [tabs.nth(i).inner_text().strip() for i in range(tabs.count())]
    assert titles, (
        "The form rendered no fieldset tabs. Volto draws them only when the "
        "schema carries more than one fieldset, so this is either a schema that "
        "arrived flat or a capture taken before the remount finished."
    )
    print(f"\nTabs for the {DRIVER_TITLE} driver: {titles}")

    # One capture per tab, in the order the schema puts them. Full page rather
    # than the window: the mapping tab's rows run past 810 pixels, and a
    # windowed capture of it stops just above the group map.
    for index, title in enumerate(titles):
        tabs.nth(index).click()
        page.wait_for_timeout(250)
        slug = title.lower().replace(" ", "-")
        _shoot(page, f"{index + 3:02d}-tab-{slug}", full_page=True)

        for field in WATCHED:
            value = _field_value(page, field)
            if value is not None:
                print(f"  [{title}] {field} = {json.dumps(value)}")

    print(f"\nDiagnostic images in {OUT}")
