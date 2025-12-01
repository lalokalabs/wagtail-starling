# Wagtail Starling

A Wagtail CMS extension that adds a "Translations" tab to all pages in the Wagtail admin interface.

## Features

- Automatically adds a "Translations" tab to all Page models in Wagtail admin
- Displays links to existing translations of the current page
- Provides quick access to add new translations via simple-translation integration

## Requirements

- Python >= 3.10
- Wagtail >= 6.4.1

## Installation

```bash
pip install wagtail-starling
```

## Configuration

Add `wagtail_starling` to your `INSTALLED_APPS` in your Django settings:

```python
INSTALLED_APPS = [
    # ... other apps
    'wagtail_starling',
    # ... wagtail apps
]
```

## License

See LICENSE file for details.
