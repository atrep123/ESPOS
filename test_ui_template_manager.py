#!/usr/bin/env python3
"""
Tests for UI Template Manager module
"""

import os
import tempfile

import pytest

from ui_template_manager import (
    Template,
    TemplateLibrary,
    TemplateMetadata,
)


@pytest.fixture
def temp_storage():
    """Create temporary storage file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_template_metadata_creation():
    """Test TemplateMetadata creation"""
    metadata = TemplateMetadata(
        name="Test Template",
        category="Layouts",
        description="Test description",
        author="Tester",
        tags=["test", "layout"]
    )
    
    assert metadata.name == "Test Template"
    assert metadata.category == "Layouts"
    assert metadata.description == "Test description"
    assert metadata.author == "Tester"
    assert metadata.tags == ["test", "layout"]


def test_template_metadata_default_tags():
    """Test TemplateMetadata with default tags"""
    metadata = TemplateMetadata(
        name="Test",
        category="Forms",
        description="Desc"
    )
    
    assert metadata.tags == []
    assert metadata.author == "User"


def test_template_creation():
    """Test Template creation and serialization"""
    metadata = TemplateMetadata(
        name="Test Template",
        category="Dashboards",
        description="Test dashboard",
        tags=["dashboard", "test"]
    )
    
    # Create mock scene
    scene = type('Scene', (), {
        'name': 'test_scene',
        'widgets': [],
        '_raw_data': {
            'name': 'test_scene',
            'widgets': [
                {'type': 'label', 'x': 0, 'y': 0, 'width': 100, 'height': 20, 'text': 'Test'}
            ]
        }
    })()
    
    template = Template(metadata, scene)
    
    # Test serialization
    data = template.to_dict()
    assert 'metadata' in data
    assert 'scene' in data
    assert data['metadata']['name'] == "Test Template"
    assert data['metadata']['category'] == "Dashboards"


def test_template_from_dict():
    """Test Template deserialization"""
    data = {
        "metadata": {
            "name": "Imported Template",
            "category": "Forms",
            "description": "Imported form",
            "author": "User",
            "tags": ["form", "imported"]
        },
        "scene": {
            "name": "imported_scene",
            "widgets": [
                {"type": "button", "x": 10, "y": 10, "width": 50, "height": 15, "text": "Click"}
            ]
        }
    }
    
    template = Template.from_dict(data)
    
    assert template.metadata.name == "Imported Template"
    assert template.metadata.category == "Forms"
    assert template.metadata.tags == ["form", "imported"]
    assert hasattr(template.scene, '_raw_data')


def test_template_library_creation(temp_storage):
    """Test TemplateLibrary initialization"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    assert isinstance(library.templates, list)
    assert library.storage_path == temp_storage
    # Default templates should be created
    assert len(library.templates) >= 3  # Dashboard, Form, Dialog


def test_template_library_categories(temp_storage):
    """Test TemplateLibrary category list"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    expected_categories = [
        "Layouts", "Forms", "Dashboards", "Dialogs",
        "Navigation", "Data Display", "Custom"
    ]
    
    assert library.CATEGORIES == expected_categories


def test_add_template(temp_storage):
    """Test adding a template to library"""
    library = TemplateLibrary(storage_path=temp_storage)
    initial_count = len(library.templates)
    
    metadata = TemplateMetadata(
        name="New Template",
        category="Custom",
        description="Custom template"
    )
    scene = type('Scene', (), {'_raw_data': {'name': 'custom', 'widgets': []}})()
    template = Template(metadata, scene)
    
    library.add_template(template)
    
    assert len(library.templates) == initial_count + 1
    assert template in library.templates


def test_remove_template(temp_storage):
    """Test removing a template from library"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    # Add a template
    metadata = TemplateMetadata(
        name="To Remove",
        category="Custom",
        description="Will be removed"
    )
    scene = type('Scene', (), {'_raw_data': {'name': 'remove', 'widgets': []}})()
    template = Template(metadata, scene)
    
    library.add_template(template)
    count_after_add = len(library.templates)
    
    # Remove it
    library.remove_template(template)
    
    assert len(library.templates) == count_after_add - 1
    assert template not in library.templates


def test_get_templates_by_category(temp_storage):
    """Test filtering templates by category"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    # Add templates in different categories
    for i, category in enumerate(['Forms', 'Dashboards', 'Forms']):
        metadata = TemplateMetadata(
            name=f"Template {i}",
            category=category,
            description="Test"
        )
        scene = type('Scene', (), {'_raw_data': {'name': f'scene{i}', 'widgets': []}})()
        library.add_template(Template(metadata, scene))
    
    forms = library.get_templates_by_category('Forms')
    dashboards = library.get_templates_by_category('Dashboards')
    
    # At least 2 Forms (plus default)
    assert len(forms) >= 2
    # At least 1 Dashboard (plus default)
    assert len(dashboards) >= 1
    
    # All returned templates should be in correct category
    for template in forms:
        assert template.metadata.category == 'Forms'


def test_search_templates(temp_storage):
    """Test searching templates"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    # Add searchable templates
    metadata1 = TemplateMetadata(
        name="Login Form",
        category="Forms",
        description="User login form with username and password",
        tags=["login", "auth"]
    )
    scene1 = type('Scene', (), {'_raw_data': {'name': 'login', 'widgets': []}})()
    library.add_template(Template(metadata1, scene1))
    
    metadata2 = TemplateMetadata(
        name="Registration Form",
        category="Forms",
        description="User registration with email",
        tags=["register", "signup"]
    )
    scene2 = type('Scene', (), {'_raw_data': {'name': 'register', 'widgets': []}})()
    library.add_template(Template(metadata2, scene2))
    
    # Search by name
    results = library.search_templates("login")
    assert len(results) >= 1
    assert any(t.metadata.name == "Login Form" for t in results)
    
    # Search by description
    results = library.search_templates("email")
    assert len(results) >= 1
    assert any(t.metadata.name == "Registration Form" for t in results)
    
    # Search by tag
    results = library.search_templates("auth")
    assert len(results) >= 1
    assert any(t.metadata.name == "Login Form" for t in results)


def test_persistence(temp_storage):
    """Test template library persistence"""
    # Create library and add template
    library1 = TemplateLibrary(storage_path=temp_storage)
    initial_count = len(library1.templates)
    
    metadata = TemplateMetadata(
        name="Persistent Template",
        category="Custom",
        description="Should persist"
    )
    scene = type('Scene', (), {'_raw_data': {'name': 'persist', 'widgets': []}})()
    library1.add_template(Template(metadata, scene))
    
    # Create new library instance from same storage
    library2 = TemplateLibrary(storage_path=temp_storage)
    
    # Should have same number of templates
    assert len(library2.templates) == initial_count + 1
    
    # Should find the added template
    found = any(t.metadata.name == "Persistent Template" for t in library2.templates)
    assert found


def test_default_dashboard_template(temp_storage):
    """Test default dashboard template structure"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    dashboards = library.get_templates_by_category('Dashboards')
    assert len(dashboards) > 0
    
    # Find the default dashboard
    dashboard = next((t for t in dashboards if 'Dashboard' in t.metadata.name), None)
    assert dashboard is not None
    
    # Check metadata
    assert dashboard.metadata.category == 'Dashboards'
    assert 'dashboard' in dashboard.metadata.tags
    
    # Check scene has widgets
    scene_data = dashboard.scene._raw_data
    assert 'widgets' in scene_data
    assert len(scene_data['widgets']) > 0


def test_default_form_template(temp_storage):
    """Test default form template structure"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    forms = library.get_templates_by_category('Forms')
    assert len(forms) > 0
    
    # Find the default form
    form = next((t for t in forms if 'Settings' in t.metadata.name or 'Form' in t.metadata.name), None)
    assert form is not None
    
    # Check metadata
    assert form.metadata.category == 'Forms'
    
    # Check scene has widgets (should have labels, inputs, button)
    scene_data = form.scene._raw_data
    assert 'widgets' in scene_data
    widgets = scene_data['widgets']
    assert len(widgets) > 0
    
    # Should have various widget types
    widget_types = {w['type'] for w in widgets}
    assert 'label' in widget_types


def test_default_dialog_template(temp_storage):
    """Test default dialog template structure"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    dialogs = library.get_templates_by_category('Dialogs')
    assert len(dialogs) > 0
    
    # Find the default dialog
    dialog = next((t for t in dialogs if 'Confirm' in t.metadata.name or 'Dialog' in t.metadata.name), None)
    assert dialog is not None
    
    # Check metadata
    assert dialog.metadata.category == 'Dialogs'
    
    # Check scene has widgets (should have panel, label, buttons)
    scene_data = dialog.scene._raw_data
    assert 'widgets' in scene_data
    widgets = scene_data['widgets']
    assert len(widgets) >= 3  # At least panel, message, button


def test_export_import_roundtrip(temp_storage):
    """Test exporting and importing a template"""
    library = TemplateLibrary(storage_path=temp_storage)
    
    # Create a template
    metadata = TemplateMetadata(
        name="Export Test",
        category="Custom",
        description="Test export/import",
        tags=["test", "export"]
    )
    scene = type('Scene', (), {
        '_raw_data': {
            'name': 'export_test',
            'widgets': [
                {'type': 'label', 'x': 10, 'y': 10, 'width': 100, 'height': 20, 'text': 'Export Test'}
            ]
        }
    })()
    original_template = Template(metadata, scene)
    
    # Serialize to dict (simulates export)
    exported_data = original_template.to_dict()
    
    # Deserialize from dict (simulates import)
    imported_template = Template.from_dict(exported_data)
    
    # Check metadata preserved
    assert imported_template.metadata.name == "Export Test"
    assert imported_template.metadata.category == "Custom"
    assert imported_template.metadata.description == "Test export/import"
    assert imported_template.metadata.tags == ["test", "export"]
    
    # Check scene data preserved
    scene_data = imported_template.scene._raw_data
    assert scene_data['name'] == 'export_test'
    assert len(scene_data['widgets']) == 1
    assert scene_data['widgets'][0]['text'] == 'Export Test'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
