# Wagtail Starling

A Wagtail CMS extension providing reusable components for multilingual content management.

## Features

- **Translation Tab**: Adds a "Translations" tab to all Page models in Wagtail admin
- **Base Article Page**: Abstract page model with SEO fields, featured images, and excerpt
- **Base Article Index Page**: Article listing with pagination and category routing
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

### Base Article Page

`BaseArticlePage` provides a reusable foundation for blog/article pages with common fields:

```python
from wagtail_starling.models import BaseArticlePage, CategoryMixin
from wagtail.fields import StreamField

# Simple article without categories
class BlogPost(BaseArticlePage):
    body = StreamField([...])

# Article with category support
class ArticlePage(CategoryMixin, BaseArticlePage):
    body = StreamField([...])
    author = ForeignKey('people.Author', ...)
```

**Included Fields:**
- `excerpt` - Brief description for listings and SEO
- `meta_description` - SEO meta description
- `featured_image` - Featured image for hero and social sharing
- `og_image` - Open Graph image (optional, falls back to featured_image)
- `canonical_url` - Canonical URL if content published elsewhere

**Included Methods:**
- `get_meta_description()` - Returns meta_description with fallback to excerpt
- `get_og_image()` - Returns og_image with fallback to featured_image
- `save()` - Preserves slug when translating to prevent non-ASCII slugs

### Base Article Index Page

`BaseArticleIndexPage` provides article listing with category routing and pagination:

```python
from wagtail_starling.models import BaseArticleIndexPage
from wagtail.contrib.routable_page.models import RoutablePageMixin

class ArticleIndexPage(BaseArticleIndexPage, RoutablePageMixin):
    intro = models.CharField(max_length=250)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def get_article_model(self):
        from myapp.models import ArticlePage
        return ArticlePage
```

**Included Features:**
- Article listing with pagination (uses `settings.ARTICLES_PER_PAGE`)
- Category filter display in context
- Category-based routing (via CategoryRoutingMixin)
- Slug preservation for translations
- `get_context()` automatically provides `articles` and `categories`

**Context Variables:**
- `articles` - Paginated article queryset
- `categories` - All categories for filter pills

### Category System

Create category-enabled pages with automatic routing:

```python
from wagtail_starling.models import Category, CategoryMixin, CategoryRoutingMixin
from wagtail.contrib.routable_page.models import RoutablePageMixin
from wagtail.models import Page

# Add category field to your article model
# IMPORTANT: CategoryMixin must come before Page for URL generation to work
class ArticlePage(CategoryMixin, Page):
    # Inherits a category ForeignKey field
    # URLs automatically include category slug when assigned
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
