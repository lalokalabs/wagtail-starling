#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Reusable models for Wagtail projects"""

from django.db import models
from django.http import Http404
from django.utils.text import slugify
from wagtail.models import TranslatableMixin
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel


@register_snippet
class Category(TranslatableMixin, models.Model):
    """Category snippet for organizing content"""

    id = models.BigAutoField(primary_key=True)
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
    """Mixin to add category field to any model"""

    category = models.ForeignKey(
        "wagtail_starling.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


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

