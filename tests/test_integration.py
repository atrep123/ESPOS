from ui_designer import UIDesigner, WidgetConfig


def test_full_workflow_save_load_export(designer_with_scene, temp_json, tmp_path):
    designer, scene, _ = designer_with_scene
    # Modify widget
    scene.widgets[0].text = "Hello"
    scene.widgets.append(WidgetConfig(type="label", x=5, y=5, width=8, height=3, text="Hi"))

    designer.save_to_json(str(temp_json))
    assert temp_json.exists()

    # Load into a fresh instance
    new_designer = UIDesigner()
    new_designer.load_from_json(str(temp_json))
    assert len(new_designer.scenes[new_designer.current_scene].widgets) == 2
    assert new_designer.scenes[new_designer.current_scene].widgets[0].text == "Hello"

    # Export code
    out_py = tmp_path / "scene_export.py"
    new_designer.export_code(str(out_py))
    assert out_py.exists()


def test_validate_design_passes_for_valid_app(make_app):
    from cyberpunk_designer.io_ops import validate_design

    app = make_app(widgets=[WidgetConfig(type="label", x=0, y=0, width=40, height=16, text="OK")])
    errors = validate_design(app)
    assert errors == []


def test_make_app_fixture_creates_working_app(make_app):
    app = make_app()
    sc = app.state.current_scene()
    assert sc is not None
    assert len(sc.widgets) == 0


def test_make_app_fixture_with_widgets(make_app):
    app = make_app(widgets=[WidgetConfig(type="box", x=0, y=0, width=20, height=20)])
    sc = app.state.current_scene()
    assert len(sc.widgets) == 1
    assert sc.widgets[0].type == "box"
