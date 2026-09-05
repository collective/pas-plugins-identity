"""Capture the control panels an administrator works in."""

from .conftest import IDP

import pytest


@pytest.mark.site(IDP)
def test_providers_control_panel(page_as_admin, shot) -> None:
    """The list of configured providers."""
    page_as_admin.goto(f"{IDP}/controlpanel/identity-providers")
    page_as_admin.wait_for_load_state("networkidle")
    shot.capture("providers-control-panel")


@pytest.mark.site(IDP)
def test_provider_form_tabs(page_as_admin, shot) -> None:
    """A provider's form, showing the tabs the driver's fieldsets produce.

    The tabs are the point of this one: a reader who has read
    {doc}`/reference/provider-form` should recognize the arrangement.

    The row's edit control is an icon button, so it is found by its accessible
    label. Clicking the provider's *name* hits a table cell and does nothing at
    all -- which the first version of this script did, capturing the list a
    second time under this name and passing.
    """
    page_as_admin.goto(f"{IDP}/controlpanel/identity-providers")
    page_as_admin.wait_for_load_state("networkidle")

    row = page_as_admin.locator("tr", has_text="GitHub")
    row.get_by_label("Edit").click()

    # Prove the form opened. A click that lands on nothing leaves the list on
    # screen, and the capture then shows the wrong page without failing.
    page_as_admin.wait_for_selector("text=Accounts", timeout=15_000)
    shot.capture("provider-form-tabs")


@pytest.mark.site(IDP)
def test_clients_control_panel(page_as_admin, shot) -> None:
    """The registered OAuth clients, on a site running the server layer."""
    page_as_admin.goto(f"{IDP}/controlpanel/identity-clients")
    page_as_admin.wait_for_load_state("networkidle")
    shot.capture("clients-control-panel")
