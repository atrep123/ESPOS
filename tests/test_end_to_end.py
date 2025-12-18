from ui_designer import WidgetConfig


def test_end_to_end_user_actions(designer_with_scene):
    designer, scene, _ = designer_with_scene
    # Add widgets
    scene.widgets.append(WidgetConfig(type="button", x=10, y=12, width=20, height=8, text="Go"))
    scene.widgets.append(WidgetConfig(type="gauge", x=30, y=6, width=12, height=20, value=50))

    # Auto layout grid then align/distribute
    designer.auto_layout(layout_type="grid", spacing=4, scene_name=scene.name)
    designer.align_widgets("center_h", [0, 1], scene_name=scene.name)
    designer.distribute_widgets("horizontal", [0, 1, 2], scene_name=scene.name)

    # Ensure positions are within bounds
    for w in scene.widgets:
        assert 0 <= w.x <= scene.width
        assert 0 <= w.y <= scene.height
