# Capturing the documentation's screenshots

The images in this documentation are not captured by hand. Scripts drive a
browser with [Playwright](https://playwright.dev/python/) and write each screen
into `docs/_static/screens/`, under the name the Markdown already references.

The reason is maintenance. One change to Volto's interface invalidates dozens of
captures at once. Redoing them by hand costs an afternoon, and the result differs
from the previous one in framing, size and example content. Here it costs one
run.

## Prepare

```shell
make screenshots-install
```

That installs the dependencies and the browser.

The scripts drive the **demo stack**, so start it first, from the repository
root:

```shell
make demo-stack-start
```

If the stack is not answering, the whole run skips with a message saying so
rather than failing with a wall of connection errors.

## Run

```shell
make screenshots-coverage   # what is still missing — opens no browser
make screenshots            # capture everything
```

## The list is not maintained here

It is deduced from the Markdown, by `scripts/generate_placeholders.py` — the same
mechanism that generates the placeholders. Keeping a second list would mean
keeping it up to date, and it would not stay so.

Two rules follow, and the code enforces both:

- **Only a screenshot the Markdown references is captured.** A misspelled name
  fails immediately, with a list of near misses. No orphan image reaches the
  repository.
- **Every image in the directory is referenced by some page.**
  `test_no_orphan_images` checks that, and it runs today.

A third, `test_every_screenshot_has_a_script`, closes the cycle in the other
direction. It is skipped while coverage is being built up; when the scripts cover
every referenced screen, the skip comes off.

## Placeholders

A screenshot referenced in the Markdown but not captured yet gets a generated
placeholder carrying its name and its `:alt:` text, so the gap is visible in the
built site rather than a broken image:

```shell
make screenshots-placeholders
```

Placeholders carry a mark in their PNG metadata, so regenerating them never
overwrites a real capture.

## Writing a script

A typical script prepares its state through the REST API and uses the browser
only to photograph:

```python
@pytest.mark.site(IDP)
def test_providers_control_panel(page_as_admin, shot) -> None:
    """The list of configured providers."""
    page_as_admin.goto(f"{IDP}/controlpanel/identity-providers")
    page_as_admin.wait_for_load_state("networkidle")
    shot.capture("providers-control-panel")
```

Preparing state through the API rather than the interface is deliberate: it is
faster, and it does not break when a button the screen does not even show is
relabelled.

### Framing

`shot.capture` takes three framings, in order of preference:

```python
shot.capture("name")                                    # the whole window
shot.capture("name", element=page.locator("#toolbar"))  # one element
shot.capture("name", clip={"x": 0, "y": 0, "width": 1440, "height": 220})
```

Clipping by region is for when there is no reliable selector.

### Stability

A capture that changes on every run produces a diff when nothing has changed, and
reviewing the pull request stops meaning anything. Before each capture the script
turns off animations, transitions and the blinking caret, blurs the focused
element, moves the pointer away, and waits for the network to settle.

Whatever still varies — dates, the name of whoever is signed in — is masked:

```python
shot.capture("name", mask=[page.locator(".last-login")])
```

Use `keep_focus=True` for any screen showing an open dropdown. Those close when
they lose focus, so the capture would otherwise show the control closed, with no
error, and show something other than what the alt text promises.

## Authentication

Signing in writes the token the REST API returned into the browser, rather than
filling in the form. The capture does not depend on the login page's markup, and
the scripts do not repeat that form dozens of times.

The login page itself, where it appears in the documentation, is captured by a
script that uses `anonymous_page` instead.

## Credentials

All of them are public: the demo stack's credentials are fixed literals in
`backend/demo/src/identitydemo/settings.py`. There is no `.env` to fill in, and
nothing here should ever be pointed at a real site.
