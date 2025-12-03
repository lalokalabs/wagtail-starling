"""
Tests for AnalyticsSettings model
"""
import pytest
from django.test import RequestFactory
from wagtail.models import Site, Page
from wagtail.test.utils import WagtailPageTestCase
from wagtail_starling.models import AnalyticsSettings


@pytest.mark.django_db
class TestAnalyticsSettings:
    """Test AnalyticsSettings model and methods"""
    
    @pytest.fixture
    def site(self):
        """Create a test site"""
        return Site.objects.get(is_default_site=True)
    
    @pytest.fixture
    def analytics_settings(self, site):
        """Create analytics settings for testing"""
        return AnalyticsSettings.objects.create(
            site=site,
            enabled=True,
            head_tracking_code='<script>console.log("test");</script>',
            body_tracking_code='<noscript>No JS</noscript>',
            inclusion_mode=AnalyticsSettings.INCLUSION_ALL,
        )
    
    @pytest.fixture
    def test_page(self):
        """Create a test page"""
        root = Page.objects.get(depth=1)
        page = Page(title="Test Page", slug="test-page")
        root.add_child(instance=page)
        return page
    
    def test_analytics_settings_creation(self, site):
        """Test creating AnalyticsSettings instance"""
        settings = AnalyticsSettings.objects.create(
            site=site,
            enabled=True,
            head_tracking_code='<script>GA4</script>',
            body_tracking_code='<noscript>No JS</noscript>',
        )
        
        assert settings.enabled is True
        assert settings.head_tracking_code == '<script>GA4</script>'
        assert settings.body_tracking_code == '<noscript>No JS</noscript>'
        assert settings.inclusion_mode == AnalyticsSettings.INCLUSION_ALL
    
    def test_analytics_settings_defaults(self, site):
        """Test default values for AnalyticsSettings"""
        settings = AnalyticsSettings.objects.create(site=site)
        
        assert settings.enabled is False
        assert settings.head_tracking_code == ''
        assert settings.body_tracking_code == ''
        assert settings.inclusion_mode == AnalyticsSettings.INCLUSION_ALL
    
    def test_should_include_analytics_when_disabled(self, analytics_settings, test_page):
        """Test that analytics is not included when disabled"""
        analytics_settings.enabled = False
        analytics_settings.save()
        
        assert analytics_settings.should_include_analytics(test_page) is False
    
    def test_should_include_analytics_mode_all(self, analytics_settings, test_page):
        """Test inclusion mode 'all' includes all pages"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_ALL
        analytics_settings.save()
        
        assert analytics_settings.should_include_analytics(test_page) is True
    
    def test_should_include_analytics_mode_specific_included(
        self, analytics_settings, test_page
    ):
        """Test inclusion mode 'specific' includes only selected pages"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_SPECIFIC
        analytics_settings.save()
        analytics_settings.included_pages.add(test_page)
        
        assert analytics_settings.should_include_analytics(test_page) is True
    
    def test_should_include_analytics_mode_specific_not_included(
        self, analytics_settings, test_page
    ):
        """Test inclusion mode 'specific' excludes non-selected pages"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_SPECIFIC
        analytics_settings.save()
        # Don't add test_page to included_pages
        
        assert analytics_settings.should_include_analytics(test_page) is False
    
    def test_should_include_analytics_mode_exclude_not_excluded(
        self, analytics_settings, test_page
    ):
        """Test inclusion mode 'exclude' includes pages not in exclusion list"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_EXCLUDE
        analytics_settings.save()
        # Don't add test_page to excluded_pages
        
        assert analytics_settings.should_include_analytics(test_page) is True
    
    def test_should_include_analytics_mode_exclude_excluded(
        self, analytics_settings, test_page
    ):
        """Test inclusion mode 'exclude' excludes selected pages"""
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_EXCLUDE
        analytics_settings.save()
        analytics_settings.excluded_pages.add(test_page)
        
        assert analytics_settings.should_include_analytics(test_page) is False
    
    def test_multiple_pages_specific_mode(self, analytics_settings):
        """Test specific mode with multiple pages"""
        root = Page.objects.get(depth=1)
        
        page1 = Page(title="Page 1", slug="page-1")
        root.add_child(instance=page1)
        
        page2 = Page(title="Page 2", slug="page-2")
        root.add_child(instance=page2)
        
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_SPECIFIC
        analytics_settings.save()
        analytics_settings.included_pages.add(page1)
        
        assert analytics_settings.should_include_analytics(page1) is True
        assert analytics_settings.should_include_analytics(page2) is False
    
    def test_multiple_pages_exclude_mode(self, analytics_settings):
        """Test exclude mode with multiple pages"""
        root = Page.objects.get(depth=1)
        
        page1 = Page(title="Page 1", slug="page-1")
        root.add_child(instance=page1)
        
        page2 = Page(title="Page 2", slug="page-2")
        root.add_child(instance=page2)
        
        analytics_settings.inclusion_mode = AnalyticsSettings.INCLUSION_EXCLUDE
        analytics_settings.save()
        analytics_settings.excluded_pages.add(page2)
        
        assert analytics_settings.should_include_analytics(page1) is True
        assert analytics_settings.should_include_analytics(page2) is False
    
    def test_inclusion_mode_choices(self):
        """Test that inclusion mode choices are defined correctly"""
        assert AnalyticsSettings.INCLUSION_ALL == 'all'
        assert AnalyticsSettings.INCLUSION_SPECIFIC == 'specific'
        assert AnalyticsSettings.INCLUSION_EXCLUDE == 'exclude'
        
        choice_values = [choice[0] for choice in AnalyticsSettings.INCLUSION_CHOICES]
        assert 'all' in choice_values
        assert 'specific' in choice_values
        assert 'exclude' in choice_values
    
    def test_verbose_name(self):
        """Test model verbose name"""
        assert AnalyticsSettings._meta.verbose_name == "Analytics Settings"
    
    def test_one_to_one_with_site(self, site):
        """Test that only one AnalyticsSettings can exist per site"""
        AnalyticsSettings.objects.create(site=site, enabled=True)
        
        # Attempting to create another should raise an error
        with pytest.raises(Exception):
            AnalyticsSettings.objects.create(site=site, enabled=False)
