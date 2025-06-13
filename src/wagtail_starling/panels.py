from wagtail.admin.panels import HelpPanel, ObjectList, TabbedInterface

translations_panels = [
    HelpPanel(template="wagtail_starling/tab_translations.html"),
]

def inject_custom_tab(edit_handler, page_class):
    """
    Function to inject the custom tab into the existing edit_handler.
    """
    edit_handler = TabbedInterface([
        ObjectList(translations_panels, heading='Translations')
    ])
    return edit_handler
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
