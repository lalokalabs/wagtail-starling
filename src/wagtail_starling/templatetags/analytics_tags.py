"""Template tags for analytics integration"""

from django import template
from django.utils.safestring import mark_safe
from wagtail.models import Site

register = template.Library()


@register.simple_tag(takes_context=True)
def analytics_head(context):
    """
    Include analytics tracking code in <head> section.

    Usage in template:
        {% load analytics_tags %}
        <head>
            ...
            {% analytics_head %}
        </head>
    """
    request = context.get('request')
    page = context.get('page')

    if not request or not page:
        return ''

    try:
        from wagtail_starling.models import AnalyticsSettings
        site = Site.find_for_request(request)
        analytics = AnalyticsSettings.for_site(site)

        if analytics.should_include_analytics(page):
            return mark_safe(analytics.head_tracking_code)
    except Exception:
        # Fail silently if settings not configured
        pass

    return ''


@register.simple_tag(takes_context=True)
def analytics_body(context):
    """
    Include analytics tracking code at end of <body> section.

    Usage in template:
        {% load analytics_tags %}
        <body>
            ...
            {% analytics_body %}
        </body>
    """
    request = context.get('request')
    page = context.get('page')

    if not request or not page:
        return ''

    try:
        from wagtail_starling.models import AnalyticsSettings
        site = Site.find_for_request(request)
        analytics = AnalyticsSettings.for_site(site)

        if analytics.should_include_analytics(page):
            return mark_safe(analytics.body_tracking_code)
    except Exception:
        # Fail silently if settings not configured
        pass

    return ''
