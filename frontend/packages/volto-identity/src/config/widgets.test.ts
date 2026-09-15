import { describe, expect, it } from 'vitest';

import install from './widgets';
import OrderedObjectListWidget, {
  SocialLinksWidget,
} from '../components/Widgets/OrderedObjectListWidget/OrderedObjectListWidget';
import OrderedStringListWidget from '../components/Widgets/OrderedStringListWidget/OrderedStringListWidget';
import ProviderIconWidget from '../components/Widgets/ProviderIconWidget';

/**
 * Install the widgets into a configuration holding only some widgets.
 *
 * @param widget What was registered by name before.
 * @returns The widgets by name afterwards.
 */
function configured(widget: Record<string, unknown> = {}) {
  const config: any = { widgets: { widget } };
  install(config);
  return config.widgets.widget;
}

describe('install', () => {
  it('registers every widget under the name a backend asks for', () => {
    const widgets = configured();

    expect(widgets.provider_icon).toBe(ProviderIconWidget);
    expect(widgets.identity_string_list).toBe(OrderedStringListWidget);
    expect(widgets.identity_object_list).toBe(OrderedObjectListWidget);
  });

  it("replaces volto-social-media's widget when it was registered first", () => {
    // Add-on configuration runs in the order the add-ons are listed, so this
    // is the case where volto-identity comes after volto-social-media.
    const theirs = () => null;

    expect(
      configured({ social_media_object_list: theirs }).social_media_object_list,
    ).toBe(SocialLinksWidget);
  });

  it('keeps the widgets already registered', () => {
    const token = () => null;

    expect(configured({ token }).token).toBe(token);
  });
});
