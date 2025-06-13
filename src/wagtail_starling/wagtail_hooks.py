# wagtail_custom_tabs/hooks.py
from wagtail import hooks
from wagtail.models import Page
from wagtail.admin import widgets as wagtailadmin_widgets

# Define a custom hook to modify the edit_handler
@hooks.register('before_edit_page')
def add_custom_tab_to_pages(request, page):
    """
    Hook to modify the edit_handler for all Page-derived models.
    """
    original_edit_handler = page.get_edit_handler()
    modified_edit_handler = inject_custom_tab(original_edit_handler, page.__class__)
    # Replace the page's edit_handler for this request
    page.edit_handler = modified_edit_handler
    return None  # Return None to allow normal processing

@hooks.register('register_page_header_buttons')
def page_header_buttons(page, user, view_name, next_url=None):
    original_edit_handler = page.get_edit_handler()
    modified_edit_handler = inject_custom_tab(original_edit_handler, page.__class__)
    # Replace the page's edit_handler for this request
    page.edit_handler = modified_edit_handler
    yield wagtailadmin_widgets.Button(
        'A dropdown button',
        '/goes/to/a/url/',
        priority=60
    )

from wagtail.admin.panels import HelpPanel, ObjectList, TabbedInterface

translations_panels = [
    HelpPanel(template="wagtail_starling/tab_translations.html"),
]

def inject_custom_tab(edit_handler, page_class):
    """
    Function to inject the custom tab into the existing edit_handler.
    """
    if isinstance(edit_handler, TabbedInterface):
        # Get existing tabs and append the custom one
        custom_tab = ObjectList(translations_panels, heading="Translations")
        existing_tabs = edit_handler.children
        new_tabs = existing_tabs + [custom_tab]
        return TabbedInterface(new_tabs)
    elif edit_handler is None:
        # If no edit_handler exists, create a new TabbedInterface with the custom tab
        return TabbedInterface([custom_tab])
    return edit_handler

def patch_page_edit_handler():
    original_get_edit_handler = Page.get_edit_handler

    def new_get_edit_handler(cls):
        original_handler = original_get_edit_handler()
        modified_handler = inject_custom_tab(original_handler, self)
        print(f"Patched for {self.__class__.__name__}: edit_handler updated")
        return modified_handler

    Page.get_edit_handler = new_get_edit_handler

from django.utils.translation import gettext_lazy

from wagtail.admin.forms.pages import WagtailAdminPageForm
from wagtail.models import Page
from wagtail.utils.decorators import cached_classmethod

Page.base_form_class = WagtailAdminPageForm


@cached_classmethod
def _get_page_edit_handler(cls):
    """
    Get the panel to use in the Wagtail admin when editing this page type.
    """
    if hasattr(cls, "edit_handler"):
        edit_handler = cls.edit_handler
    else:
        # construct a TabbedInterface made up of content_panels, promote_panels
        # and settings_panels, skipping any which are empty
        tabs = []

        if cls.content_panels:
            tabs.append(ObjectList(cls.content_panels, heading=gettext_lazy("Content")))
        if cls.promote_panels:
            tabs.append(ObjectList(cls.promote_panels, heading=gettext_lazy("Promote")))
        if cls.settings_panels:
            tabs.append(
                ObjectList(cls.settings_panels, heading=gettext_lazy("Settings"))
            )

        edit_handler = TabbedInterface(tabs, base_form_class=cls.base_form_class)
        edit_handler = inject_custom_tab(edit_handler, cls.base_form_class)

    return edit_handler.bind_to_model(cls)


Page.get_edit_handler = _get_page_edit_handler
