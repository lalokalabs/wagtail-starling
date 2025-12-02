# Wagtail Starling

A Wagtail CMS extension providing reusable components for multilingual content management.

## Features

- **Translation Tab**: Adds a "Translations" tab to all Page models in Wagtail admin
- **Category System**: Translatable category snippets with automatic routing and URL handling
- **Category Routing**: Built-in support for category-based article URLs with pagination

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

## Usage

### Category System

Create category-enabled pages with automatic routing:

```python
from wagtail_starling.models import Category, CategoryMixin, CategoryRoutingMixin
from wagtail.contrib.routable_page.models import RoutablePageMixin
from wagtail.models import Page

# Add category field to your article model
class ArticlePage(Page, CategoryMixin):
    # Inherits a category ForeignKey field
    body = RichTextField()

# Enable category-based routing
class ArticleIndexPage(CategoryRoutingMixin, RoutablePageMixin, Page):
    intro = CharField(max_length=250)

    def get_article_model(self):
        return ArticlePage
```

**URL Patterns:**
- `/articles/` - All articles
- `/articles/<category-slug>/` - Articles in category
- `/articles/<category-slug>/<article-slug>/` - Article with category

**Default Template:** Includes `wagtail_starling/category_index_page.html` which extends `base.html`. Override by creating `<app_label>/category_index_page.html` in your project.

## License

See LICENSE file for details.
