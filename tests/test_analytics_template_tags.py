"""
Tests for analytics template tags
"""
import pytest
from django.template import Template, Context
from django.test import RequestFactory
from wagtail.models import Site, Page
from wagtail_starling.models import AnalyticsSettings


@pytest.mark.django_db
class TestAnalyticsTemplateTags:
    """Test analytics_head and analytics_body template tags"""
    
    @pytest.fixture
    def site(self):
        """Create a test site"""
        return Site.objects.get(is_default_site=True)
    
    @pytest.fixture
    def request_factory(self):
        """Create a request factory"""
        return RequestFactory()
    
    @pytest.fixture
    def test_page(self):
        """Create a test page"""
        root = Page.objects.get(depth=1)
        page = Page(title="Test Page", slug="test-page")
        root.add_child(instance=page)
        return page
    
    @pytest.fixture
    def analytics_settings(self, site):
        """Create enabled analytics settings"""
        return AnalyticsSettings.objects.create(
            site=site,
            enabled=True,
            head_tracking_code='<script>console.log("GA4");</script>',
            body_tracking_code='<noscript>No JavaScript</noscript>',
            inclusion_mode=AnalyticsSettings.INCLUSION_ALL,
        )
    
    def test_analytics_head_tag_renders_code(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that analytics_head renders tracking code"""
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert '<script>console.log("GA4");</script>' in output
    
    def test_analytics_body_tag_renders_code(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that analytics_body renders tracking code"""
        template = Template(
            "{% load analytics_tags %}{% analytics_body %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert '<noscript>No JavaScript</noscript>' in output
    
    def test_analytics_head_when_disabled(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that analytics_head returns empty when disabled"""
        analytics_settings.enabled = False
        analytics_settings.save()
        
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert output.strip() == ''
    
    def test_analytics_body_when_disabled(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that analytics_body returns empty when disabled"""
        analytics_settings.enabled = False
        analytics_settings.save()
        
        template = Template(
            "{% load analytics_tags %}{% analytics_body %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert output.strip() == ''
    
    def test_analytics_head_without_request(self, analytics_settings, test_page):
        """Test that analytics_head handles missing request gracefully"""
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        context = Context({
            'page': test_page,
        })
        
        output = template.render(context)
        assert output.strip() == ''
    
    def test_analytics_head_without_page(self, analytics_settings, request_factory, site):
        """Test that analytics_head handles missing page gracefully"""
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
        })
        
        output = template.render(context)
        assert output.strip() == ''
    
    def test_analytics_tags_with_page_exclusion(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that excluded pages don't show analytics"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_EXCLUDE
        analytics_settings.save()
        analytics_settings.excluded_pages.add(test_page)
        
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}|{% analytics_body %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert '<script>console.log("GA4");</script>' not in output
        assert '<noscript>No JavaScript</noscript>' not in output
    
    def test_analytics_tags_with_specific_inclusion(
        self, analytics_settings, request_factory, site
    ):
        """Test specific inclusion mode with included and non-included pages"""
        root = Page.objects.get(depth=1)
        
        included_page = Page(title="Included", slug="included")
        root.add_child(instance=included_page)
        
        excluded_page = Page(title="Not Included", slug="not-included")
        root.add_child(instance=excluded_page)
        
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_SPECIFIC
        analytics_settings.save()
        analytics_settings.included_pages.add(included_page)
        
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        # Test included page
        context = Context({
            'request': request,
            'page': included_page,
        })
        output = template.render(context)
        assert '<script>console.log("GA4");</script>' in output
        
        # Test non-included page
        context = Context({
            'request': request,
            'page': excluded_page,
        })
        output = template.render(context)
        assert '<script>console.log("GA4");</script>' not in output
    
    def test_analytics_tags_html_is_safe(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test that HTML in tracking code is not escaped"""
        analytics_settings.head_tracking_code = '<script src="https://example.com/track.js"></script>'
        analytics_settings.save()
        
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        # Should contain unescaped HTML
        assert '<script src="https://example.com/track.js"></script>' in output
        # Should not be escaped
        assert '&lt;script' not in output
    
    def test_both_tags_in_single_template(
        self, analytics_settings, test_page, request_factory, site
    ):
        """Test using both tags in a single template"""
        template = Template("""
            {% load analytics_tags %}
            <html>
            <head>
                {% analytics_head %}
            </head>
            <body>
                <h1>Content</h1>
                {% analytics_body %}
            </body>
            </html>
        """)
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        output = template.render(context)
        assert '<script>console.log("GA4");</script>' in output
        assert '<noscript>No JavaScript</noscript>' in output
    
    def test_analytics_without_settings_configured(
        self, test_page, request_factory, site
    ):
        """Test that tags handle missing analytics settings gracefully"""
        # Don't create analytics settings
        
        template = Template(
            "{% load analytics_tags %}{% analytics_head %}|{% analytics_body %}"
        )
        
        request = request_factory.get('/')
        request.site = site
        
        context = Context({
            'request': request,
            'page': test_page,
        })
        
        # Should not raise an error, just return empty string
        output = template.render(context)
        assert output.strip() == '|'
