#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Reusable models for Wagtail projects"""

from django.db import models
from django.http import Http404
from django.utils.text import slugify
from wagtail.models import TranslatableMixin, Page
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, PageChooserPanel
from wagtail.search import index
from wagtail.images.models import Image
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_snippet
class Category(TranslatableMixin, models.Model):
    """
    Category snippet for organizing content.

    NOTE: Do not explicitly define `id = models.BigAutoField(primary_key=True)`.
    When you explicitly define the primary key field, Django sets auto_created=False,
    which causes Wagtail's copy_for_translation to include the id in the copied data.
    This makes Django UPDATE the existing object instead of creating a new one.

    By letting Django auto-create the primary key, it sets auto_created=True,
    which Wagtail's _extract_field_data() properly excludes from the copy.

    WORKAROUND: If you must explicitly define the id field, you can override
    copy_for_translation to exclude it:

        def copy_for_translation(self, locale, exclude_fields=None):
            exclude_fields = (exclude_fields or []) + ['id']
            return super().copy_for_translation(locale, exclude_fields=exclude_fields)
    """

    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
    ]

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        unique_together = [("translation_key", "locale")]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug and preserve it when translating.
        """
        # Auto-generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name)

        # If this is a translation (has translation_key and ID not set yet),
        # try to preserve slug from source
        if self.translation_key and not self.id:
            # Find the source category with the same translation_key
            source_category = (
                Category.objects.filter(translation_key=self.translation_key)
                .exclude(locale=self.locale)
                .first()
            )
            if source_category:
                # Preserve the slug from the source category
                self.slug = source_category.slug

        super().save(*args, **kwargs)


class CategoryMixin(models.Model):
    """
    Mixin to add category field to any model.

    For Wagtail Page models, this automatically modifies URLs to include
    the category slug when a category is assigned.
    """

    category = models.ForeignKey(
        "wagtail_starling.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True

    def get_url_parts(self, request=None):
        """
        Override to return category-based URL when category is set.

        Returns URL parts for pages with category as /category-slug/page-slug/
        or /locale-prefix/category-slug/page-slug/ (preserving language prefix).

        Only applies to Wagtail Page models. Non-Page models will not have this method.
        """
        # Check if this is a Wagtail Page (has get_url_parts from parent)
        if not hasattr(super(), 'get_url_parts'):
            raise AttributeError(
                f"{self.__class__.__name__} does not inherit from Wagtail Page. "
                "CategoryMixin.get_url_parts() only works with Page models."
            )

        url_parts = super().get_url_parts(request=request)

        if url_parts is None:
            return None

        site_id, root_url, page_path = url_parts

        if self.category:
            parts = page_path.rstrip("/").split("/")
            # Only insert category slug if it's not already there
            if len(parts) >= 2 and self.category.slug not in parts:
                parts.insert(-1, self.category.slug)
                page_path = "/".join(parts) + "/"

        return (site_id, root_url, page_path)


class CategoryRoutingMixin:
    """
    Mixin for RoutablePageMixin pages that provides category-based routing.

    This mixin handles routing for:
    - Category index pages: /articles/<category-slug>/
    - Articles with categories: /articles/<category-slug>/<article-slug>/
    - Articles without categories: /articles/<article-slug>/ (redirects if category exists)

    Usage:
        class ArticleIndexPage(CategoryRoutingMixin, RoutablePageMixin, Page):
            # Your page model fields
            pass

            # Optionally override get_article_model() if not using 'ArticlePage'
            def get_article_model(self):
                from myapp.models import BlogPost
                return BlogPost
    """

    def get_article_model(self):
        """
        Override this method to specify which page model to use for articles.
        Default assumes there's an 'ArticlePage' model in the same module.
        """
        # Import here to avoid circular imports
        from django.apps import apps
        # Try to get ArticlePage from the same app
        app_label = self._meta.app_label
        try:
            return apps.get_model(app_label, 'ArticlePage')
        except LookupError:
            raise NotImplementedError(
                "You must override get_article_model() to specify the article page model"
            )

    def route(self, request, path_components):
        language = request.LANGUAGE_CODE
        ArticleModel = self.get_article_model()

        # Check for single component path - could be category index or blog post
        if len(path_components) == 1:
            slug = path_components[0]

            # First check if it's an article with category (for redirect)
            article = (
                ArticleModel.objects.live()
                .child_of(self)
                .filter(slug=slug, locale__language_code=language)
                .first()
            )

            if article and hasattr(article, 'category') and article.category:
                # Article has a category, return route with redirect_url in kwargs
                new_url = article.get_url(request=request)
                return (self, path_components, {"redirect_url": new_url})

            # Check if it's a category index
            try:
                category = Category.objects.get(
                    slug=slug, locale__language_code=language
                )
                # It's a valid category, return route result tuple
                return (self, path_components, {"category_slug": slug})
            except Category.DoesNotExist:
                pass

        # Try normal routable page routing (for tag pages, etc.)
        try:
            return super().route(request, path_components)
        except Http404:
            pass

        # Check for category + blog post (2 components)
        if len(path_components) == 2:
            category_slug, post_slug = path_components

            try:
                category = Category.objects.get(
                    slug=category_slug, locale__language_code=language
                )
                # Find the article with matching slug and category
                article = (
                    ArticleModel.objects.live()
                    .child_of(self)
                    .filter(
                        slug=post_slug,
                        category=category,
                        locale__language_code=language,
                    )
                    .first()
                )

                if article:
                    return article.specific.route(request, [])

            except Category.DoesNotExist:
                pass

        # Fall back to normal page routing (for individual blog pages without category)
        raise Http404()

    def serve(self, request, *args, **kwargs):
        """Handle category routing and redirects"""
        # Check if we need to redirect old URL to category-based URL
        if "redirect_url" in kwargs:
            from django.http import HttpResponsePermanentRedirect
            return HttpResponsePermanentRedirect(kwargs["redirect_url"])

        # Check if this is a category request
        if "category_slug" in kwargs:
            return self.article_category_index(request, kwargs["category_slug"])

        return super().serve(request, *args, **kwargs)

    def article_category_index(self, request, category_slug):
        """
        Render category index page with articles filtered by category.
        Override this method to customize the template or context.
        """
        from django.conf import settings
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

        language = request.LANGUAGE_CODE
        ArticleModel = self.get_article_model()

        category = Category.objects.get(
            slug=category_slug, locale__language_code=language
        )

        articles = (
            ArticleModel.objects.live()
            .filter(locale__language_code=language)
            .filter(category=category)
            .order_by("-first_published_at", "-id")
        )

        # Use ARTICLES_PER_PAGE setting or default to 10
        per_page = getattr(settings, 'ARTICLES_PER_PAGE', 10)
        paginator = Paginator(articles, per_page)
        page = request.GET.get("page")

        try:
            articles = paginator.page(page)
        except PageNotAnInteger:
            articles = paginator.page(1)
        except EmptyPage:
            articles = paginator.page(paginator.num_pages)

        # Get template name - can be overridden
        template_name = self.get_category_index_template()

        return self.render(
            request,
            context_overrides={
                "articles": articles,
                "category": category,
            },
            template=template_name,
        )

    def get_category_index_template(self):
        """
        Override this method to specify a custom template for category index pages.
        Default tries to find 'category_index_page.html' in the same app,
        falling back to the default wagtail_starling template if not found.
        """
        from django.template.loader import select_template

        app_label = self._meta.app_label
        template_names = [
            f"{app_label}/category_index_page.html",
            "wagtail_starling/category_index_page.html",
        ]

        # Use select_template to automatically pick the first available template
        template = select_template(template_names)
        return template.template.name



class BaseArticlePage(Page):
    """
    Abstract base class for article/blog pages.

    Provides common fields for articles including SEO, featured images,
    and excerpt. Projects should inherit from this and add their own
    content fields and mixins.

    Example:
        # Without category support
        class ArticlePage(BaseArticlePage):
            body = StreamField([...])
            author = ForeignKey('people.Author', ...)

        # With category support
        class ArticlePage(CategoryMixin, BaseArticlePage):
            body = StreamField([...])
    """

    # Short description for listings and SEO
    excerpt = models.TextField(
        blank=True,
        max_length=500,
        help_text="Brief description for listings and SEO"
    )

    # SEO fields
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="SEO meta description (recommended: 150-160 characters)",
    )
    featured_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Featured image for hero and social sharing",
    )
    og_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Open Graph image for social sharing (optional, uses featured_image if not set)",
    )
    canonical_url = models.URLField(
        blank=True,
        help_text="Canonical URL if this content was originally published elsewhere",
    )

    promote_panels = Page.promote_panels + [
        MultiFieldPanel(
            [
                FieldPanel("meta_description"),
                FieldPanel("featured_image"),
                FieldPanel("og_image"),
                FieldPanel("canonical_url"),
            ],
            heading="SEO and Social Media",
        ),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("excerpt"),
        index.SearchField("meta_description"),
    ]

    class Meta:
        abstract = True

    def get_meta_description(self):
        """Get meta description with fallback to excerpt"""
        return self.meta_description or self.excerpt or self.title

    def get_og_image(self):
        """Get Open Graph image with fallback to featured image"""
        return self.og_image or self.featured_image

    def save(self, *args, **kwargs):
        """
        Override save to preserve slug when translating pages.
        This prevents non-ASCII titles from auto-generating non-ASCII slugs.
        """
        # Check if this is a translation (has translation_key but is being created)
        if self.translation_key and not self.id:
            # Find the source page with the same translation_key
            source_page = (
                self.__class__.objects.filter(translation_key=self.translation_key)
                .exclude(locale=self.locale)
                .first()
            )
            if source_page and source_page.get_parent() != self.get_parent():
                # Only preserve slug if pages have different parents
                self.slug = source_page.slug

        super().save(*args, **kwargs)



class BaseArticleIndexPage(CategoryRoutingMixin, Page):
    """
    Abstract base class for article/blog index pages.

    NOTE: When using this class, you must also inherit from RoutablePageMixin:
        from wagtail.contrib.routable_page.models import RoutablePageMixin

        class ArticleIndexPage(BaseArticleIndexPage, RoutablePageMixin):
            ...

    Provides:
    - Category-based routing (inherited from CategoryRoutingMixin)
    - Article listing with pagination
    - Category filter display
    - Slug preservation for translations

    Projects must:
    - Inherit from this class
    - Optionally override get_article_model() to specify article page type
    - Add content panels for any custom fields

    Example:
        class ArticleIndexPage(BaseArticleIndexPage):
            intro = models.CharField(max_length=250)

            content_panels = Page.content_panels + [
                FieldPanel("intro"),
            ]

            def get_article_model(self):
                from myapp.models import ArticlePage
                return ArticlePage
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Override save to preserve slug when translating pages.
        This prevents non-ASCII titles from auto-generating non-ASCII slugs.
        """
        if self.translation_key and not self.id:
            source_page = (
                self.__class__.objects.filter(translation_key=self.translation_key)
                .exclude(locale=self.locale)
                .first()
            )
            if source_page and source_page.get_parent() != self.get_parent():
                self.slug = source_page.slug

        super().save(*args, **kwargs)

    def get_context(self, request):
        """
        Add articles and categories to context with pagination.
        """
        from django.conf import settings
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

        context = super().get_context(request)
        language = request.LANGUAGE_CODE
        ArticleModel = self.get_article_model()

        # Get all live articles in current language
        articles = (
            ArticleModel.objects.live()
            .filter(locale__language_code=language)
            .order_by("-first_published_at", "-id")
        )

        # Get categories for filter display
        categories = Category.objects.filter(
            locale__language_code=language
        ).order_by("name")

        # Paginate articles
        per_page = getattr(settings, 'ARTICLES_PER_PAGE', 10)
        paginator = Paginator(articles, per_page)
        page = request.GET.get("page")

        try:
            articles = paginator.page(page)
        except PageNotAnInteger:
            articles = paginator.page(1)
        except EmptyPage:
            articles = paginator.page(paginator.num_pages)

        context["articles"] = articles
        context["categories"] = categories

        return context


@register_setting
class AnalyticsSettings(BaseSiteSetting):
    """
    Analytics settings for Google Analytics, Matomo, or other analytics services.

    Allows admin to:
    - Configure analytics tracking code (head and body)
    - Enable/disable analytics globally
    - Include analytics on all pages by default
    - Exclude specific pages from analytics
    - Include analytics only on specific pages
    """

    id = models.BigAutoField(primary_key=True)

    INCLUSION_ALL = 'all'
    INCLUSION_SPECIFIC = 'specific'
    INCLUSION_EXCLUDE = 'exclude'

    INCLUSION_CHOICES = [
        (INCLUSION_ALL, 'Include on all pages (default)'),
        (INCLUSION_SPECIFIC, 'Include only on specific pages'),
        (INCLUSION_EXCLUDE, 'Include on all pages except specific pages'),
    ]

    # Global enable/disable
    enabled = models.BooleanField(
        default=False,
        help_text="Enable analytics tracking across the site"
    )

    # Analytics code
    head_tracking_code = models.TextField(
        blank=True,
        help_text="Analytics tracking code to insert in <head> section (e.g., Google Analytics, Matomo). Include <script> tags."
    )

    body_tracking_code = models.TextField(
        blank=True,
        help_text="Analytics tracking code to insert at the end of <body> section (e.g., Google Tag Manager noscript). Include <noscript> or <script> tags."
    )

    # Inclusion mode
    inclusion_mode = models.CharField(
        max_length=20,
        choices=INCLUSION_CHOICES,
        default=INCLUSION_ALL,
        help_text="Control which pages include analytics"
    )

    # Page selection for specific/exclude modes
    included_pages = models.ManyToManyField(
        Page,
        blank=True,
        related_name='analytics_included',
        help_text="Pages to include analytics on (when 'Include only on specific pages' is selected)"
    )

    excluded_pages = models.ManyToManyField(
        Page,
        blank=True,
        related_name='analytics_excluded',
        help_text="Pages to exclude from analytics (when 'Include on all pages except specific pages' is selected)"
    )

    panels = [
        FieldPanel('enabled'),
        MultiFieldPanel(
            [
                FieldPanel('head_tracking_code'),
                FieldPanel('body_tracking_code'),
            ],
            heading="Analytics Tracking Code",
        ),
        MultiFieldPanel(
            [
                FieldPanel('inclusion_mode'),
                PageChooserPanel('included_pages'),
                PageChooserPanel('excluded_pages'),
            ],
            heading="Page Inclusion Rules",
        ),
    ]

    class Meta:
        verbose_name = "Analytics Settings"

    def should_include_analytics(self, page):
        """
        Determine if analytics should be included on the given page.

        Args:
            page: Wagtail Page instance

        Returns:
            bool: True if analytics should be included, False otherwise
        """
        if not self.enabled:
            return False

        if self.inclusion_mode == self.INCLUSION_ALL:
            return True

        if self.inclusion_mode == self.INCLUSION_SPECIFIC:
            # Check if page is in included_pages
            return self.included_pages.filter(id=page.id).exists()

        if self.inclusion_mode == self.INCLUSION_EXCLUDE:
            # Check if page is NOT in excluded_pages
            return not self.excluded_pages.filter(id=page.id).exists()

        return False
