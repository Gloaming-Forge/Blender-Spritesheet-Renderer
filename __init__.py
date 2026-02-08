"""Spritesheet Renderer - Blender extension for automated spritesheet rendering.

Modernized for Blender 4.2+ / 5.0. Based on chrishayesmu/Blender-Spritesheet-Renderer.
"""

import bpy
from bpy.app.handlers import persistent
import functools
import importlib
import sys
from typing import Callable, List, Type, Union

print(f"[SpritesheetRenderer] Loading addon under Blender version {bpy.app.version_string} "
      f"and Python version {sys.version}")

# Module definitions for dynamic loading/reloading during development.
# Tuples represent (package, [submodules]).
_module_defs = [
    "utils",
    "property_groups",
    "operators",
    "render_operator",
    "preferences",
    "ui_lists",
    "ui_panels",
    ("util", [
        "Bounds", "Camera", "FileSystemUtil", "ImageMagick",
        "Register", "SceneSnapshot", "StringUtil", "TerminalOutput", "UIUtil"
    ])
]

_loaded_modules = {}

def _load_modules():
    """Load all addon submodules using relative imports."""
    for module_def in _module_defs:
        if isinstance(module_def, str):
            mod = importlib.import_module("." + module_def, __name__)
            importlib.reload(mod)
            _loaded_modules[module_def] = mod
        elif isinstance(module_def, tuple):
            pkg_name, submods = module_def
            for submod_name in submods:
                full_name = f".{pkg_name}.{submod_name}"
                mod = importlib.import_module(full_name, __name__)
                importlib.reload(mod)
                _loaded_modules[submod_name] = mod

_load_modules()

# Make loaded modules accessible as module-level names
utils = _loaded_modules["utils"]
property_groups = _loaded_modules["property_groups"]
operators = _loaded_modules["operators"]
render_operator = _loaded_modules["render_operator"]
preferences = _loaded_modules["preferences"]
ui_lists = _loaded_modules["ui_lists"]
ui_panels = _loaded_modules["ui_panels"]
Register = _loaded_modules["Register"]
UIUtil = _loaded_modules["UIUtil"]

print("[SpritesheetRenderer] All internal modules loaded")


# This operator is in the main file so it has the correct module path
class SPRITESHEET_OT_ShowAddonPrefsOperator(bpy.types.Operator):
    bl_idname = "spritesheet.showprefs"
    bl_label = "Open Addon Preferences"
    bl_description = "Opens the addon preferences for Spritesheet Renderer"

    def execute(self, _context):
        bpy.ops.preferences.addon_show(module=__package__)
        return {'FINISHED'}


def check_animation_state():
    """Periodically check whether animations are playing so we can keep our animation set
    status up-to-date. Unfortunately there's no event handler for animation playback
    starting/stopping."""
    # Guard against missing screen context (e.g. background/headless mode)
    try:
        screen = bpy.context.screen
        if screen is None or not screen.is_animation_playing:
            props = bpy.context.scene.SpritesheetPropertyGroup
            for animation_set in props.animation_options.animation_sets:
                animation_set.is_previewing = False
    except (AttributeError, RuntimeError):
        # context.screen doesn't exist in --background mode; silently skip
        pass

    return 1.0  # check every second


def _find_image_magick_exe():
    """Try to auto-detect ImageMagick if the path isn't already set.
    NOTE: Phase 2 will remove ImageMagick dependency entirely."""
    try:
        if not preferences.PrefsAccess.image_magick_path:
            bpy.ops.spritesheet.prefs_locate_imagemagick()
    except Exception:
        pass  # Non-critical; user can set path manually


@persistent
def _initialize_collections(_unused: None):
    """Initializes certain CollectionProperty objects that otherwise would be empty."""
    props = bpy.context.scene.SpritesheetPropertyGroup

    if len(props.camera_options.targets) == 0:
        props.camera_options.targets.add()

    if len(props.rotation_options.targets) == 0:
        props.rotation_options.targets.add()

    # Initialize animation sets
    if len(props.animation_options.animation_sets) == 0:
        control_animations = props.animation_options.control_animations
        props.animation_options.control_animations = True
        bpy.ops.spritesheet.add_animation_set()
        props.animation_options.control_animations = control_animations

    for i in range(len(props.animation_options.animation_sets)):
        ui_panels.SPRITESHEET_PT_AnimationSetPanel.create_sub_panel(i)

    # Initialize material sets
    if len(props.material_options.material_sets) == 0:
        control_materials = props.material_options.control_materials
        props.material_options.control_materials = True
        bpy.ops.spritesheet.add_material_set()
        props.material_options.control_materials = control_materials

    for i in range(len(props.material_options.material_sets)):
        ui_panels.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(i)


@persistent
def _reset_reporting_props(_unused: None):
    reporting_props = bpy.context.scene.ReportingPropertyGroup

    reporting_props.current_frame_num = 0
    reporting_props.elapsed_time = 0
    reporting_props.has_any_job_started = False
    reporting_props.job_in_progress = False
    reporting_props.last_error_message = ""
    reporting_props.output_directory = ""
    reporting_props.total_num_frames = 0


classes: List[Union[Type[bpy.types.Panel], Type[bpy.types.UIList], Type[bpy.types.Operator]]] = [
    # Property groups (order matters: dependencies first)
    property_groups.AnimationSetTargetPropertyGroup,
    property_groups.AnimationSetPropertyGroup,
    property_groups.AnimationOptionsPropertyGroup,
    property_groups.CameraTargetPropertyGroup,
    property_groups.CameraOptionsPropertyGroup,
    property_groups.MaterialSetTargetPropertyGroup,
    property_groups.MaterialSetPropertyGroup,
    property_groups.MaterialOptionsPropertyGroup,
    property_groups.ReportingPropertyGroup,
    property_groups.RotationTargetPropertyGroup,
    property_groups.RotationOptionsPropertyGroup,
    property_groups.SpritesheetPropertyGroup,

    preferences.SpritesheetAddonPreferences,

    # Operators
    SPRITESHEET_OT_ShowAddonPrefsOperator,
    operators.SPRITESHEET_OT_AddAnimationSetOperator,
    operators.SPRITESHEET_OT_AddCameraTargetOperator,
    operators.SPRITESHEET_OT_AddMaterialSetOperator,
    operators.SPRITESHEET_OT_AddRotationTargetOperator,
    operators.SPRITESHEET_OT_AssignMaterialSetOperator,
    operators.SPRITESHEET_OT_ConfigureRenderCameraOperator,
    operators.SPRITESHEET_OT_LocateImageMagickOperator,
    operators.SPRITESHEET_OT_ModifyAnimationSetOperator,
    operators.SPRITESHEET_OT_ModifyMaterialSetOperator,
    operators.SPRITESHEET_OT_MoveCameraTargetDownOperator,
    operators.SPRITESHEET_OT_MoveCameraTargetUpOperator,
    operators.SPRITESHEET_OT_MoveRotationTargetDownOperator,
    operators.SPRITESHEET_OT_MoveRotationTargetUpOperator,
    operators.SPRITESHEET_OT_OpenDirectoryOperator,
    operators.SPRITESHEET_OT_OptimizeCameraOperator,
    operators.SPRITESHEET_OT_PlayAnimationSetOperator,
    operators.SPRITESHEET_OT_RemoveAnimationSetOperator,
    operators.SPRITESHEET_OT_RemoveCameraTargetOperator,
    operators.SPRITESHEET_OT_RemoveMaterialSetOperator,
    operators.SPRITESHEET_OT_RemoveRotationTargetOperator,

    render_operator.SPRITESHEET_OT_RenderSpritesheetOperator,

    # UI property lists
    ui_lists.SPRITESHEET_UL_AnimationActionPropertyList,
    ui_lists.SPRITESHEET_UL_CameraTargetPropertyList,
    ui_lists.SPRITESHEET_UL_MaterialSetTargetPropertyList,
    ui_lists.SPRITESHEET_UL_RotationTargetPropertyList,

    # UI panels
    ui_panels.SPRITESHEET_PT_AddonPanel,
    ui_panels.SPRITESHEET_PT_OutputPropertiesPanel,
    ui_panels.SPRITESHEET_PT_AnimationsPanel,
    ui_panels.SPRITESHEET_PT_CameraPanel,
    ui_panels.SPRITESHEET_PT_MaterialsPanel,
    ui_panels.SPRITESHEET_PT_RotationOptionsPanel,
    ui_panels.SPRITESHEET_PT_JobManagementPanel
]

_timers: List[Callable] = []


def _start_timer(func: Callable, make_partial: bool = False,
                 first_interval: float = 0, is_persistent: bool = False):
    if make_partial:
        func = functools.partial(func, None)

    bpy.app.timers.register(func, first_interval=first_interval, persistent=is_persistent)
    _timers.append(func)


def register():
    for cls in classes:
        Register.register_class(cls)

    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(
        type=property_groups.SpritesheetPropertyGroup
    )
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(
        type=property_groups.ReportingPropertyGroup
    )

    # Timers for initialization and periodic checks
    _start_timer(check_animation_state, first_interval=0.1, is_persistent=True)
    _start_timer(_find_image_magick_exe, first_interval=0.1)
    _start_timer(_initialize_collections, make_partial=True)
    _start_timer(_reset_reporting_props, make_partial=True)

    bpy.app.handlers.load_post.append(_initialize_collections)
    bpy.app.handlers.load_post.append(_reset_reporting_props)


def unregister():
    for timer in _timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    bpy.app.handlers.load_post.remove(_initialize_collections)
    bpy.app.handlers.load_post.remove(_reset_reporting_props)

    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup

    UIUtil.unregister_subpanels()

    for cls in reversed(classes):
        Register.unregister_class(cls)


# Allow running from Blender's Text editor for testing
if __name__ == "__main__":
    register()
