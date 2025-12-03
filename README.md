# Wagtail Starling

A Wagtail CMS extension providing reusable components for multilingual content management.

## Features

- **Translation Tab**: Adds a "Translations" tab to all Page models in Wagtail admin
- **Base Article Page**: Abstract page model with SEO fields, featured images, and excerpt
- **Base Article Index Page**: Article listing with pagination and category routing
- **Category System**: Translatable category snippets with automatic routing and URL handling
- **Category Routing**: Built-in support for category-based article URLs with pagination
- **Analytics Settings**: Flexible analytics integration (Google Analytics, Matomo, etc.) with page-level control

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
    'wagtail.contrib.settings',  # Required for Analytics Settings
    'wagtail_starling',
    # ... wagtail apps
]
```

Add the settings context processor (required for Analytics Settings):

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                # ... other context processors
                'wagtail.contrib.settings.context_processors.settings',
            ],
        },
    },
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

## Analytics Settings

Configure site-wide analytics (Google Analytics, Matomo, or custom tracking) with flexible page-level control.

### Setup

1. Ensure `wagtail.contrib.settings` is in `INSTALLED_APPS`
2. Add settings context processor (see Configuration above)
3. Run migrations: `python manage.py migrate wagtail_starling`
4. Add template tags to your base template

### Template Integration

Add the analytics template tags to your base template:

```html
{% load analytics_tags %}
<!DOCTYPE html>
<html>
    <head>
        <!-- Your existing head content -->
        {% analytics_head %}
    </head>
    <body>
        <!-- Your page content -->
        {% analytics_body %}
    </body>
</html>
```

### Admin Configuration

Access Analytics Settings in Wagtail Admin under **Settings → Analytics Settings**:

**Global Settings:**
- **Enabled**: Enable/disable analytics tracking site-wide
- **Head Tracking Code**: Code to insert in `<head>` (e.g., Google Analytics)
- **Body Tracking Code**: Code to insert at end of `<body>` (e.g., Google Tag Manager noscript)

**Page Inclusion Rules:**
- **Include on all pages (default)**: Analytics on every page
- **Include only on specific pages**: Choose which pages get analytics
- **Include on all pages except specific pages**: Exclude certain pages (e.g., admin, private pages)

### Example: Google Analytics 4

```html
<!-- Head Tracking Code -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Example: Matomo

```html
<!-- Head Tracking Code -->
<script>
  var _paq = window._paq = window._paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u="//your-matomo-url/";
    _paq.push(['setTrackerUrl', u+'matomo.php']);
    _paq.push(['setSiteId', '1']);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
  })();
</script>

<!-- Body Tracking Code -->
<noscript><p><img src="//your-matomo-url/matomo.php?idsite=1&amp;rec=1" style="border:0;" alt="" /></p></noscript>
```

## License

See LICENSE file for details.
