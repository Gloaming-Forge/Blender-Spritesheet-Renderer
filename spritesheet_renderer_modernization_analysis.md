# Blender-Spritesheet-Renderer: Fork & Modernization Analysis

## 1. Repository Overview

**Repo:** `chrishayesmu/Blender-Spritesheet-Renderer`
**License:** MIT
**Last Release:** v2.2.2 (Sep 15, 2021)
**Commits:** 93 total
**Target Blender:** 2.90.1 only
**Language:** 100% Python
**External Dependency:** ImageMagick 7.x (subprocess calls)

### File Structure

```
Blender-Spritesheet-Renderer/
├── .vscode/                    # VSCode debug configs
├── screenshots/                # Example output images
├── util/                       # Utility modules
│   ├── CameraFitting.py        # Orthographic camera auto-fit logic
│   ├── ImageMagick.py          # ImageMagick subprocess wrapper
│   ├── SceneSnapshot.py        # Save/restore scene state (actions, rotations, selections)
│   └── UIUtil.py               # UI helper functions (message boxes, etc.)
├── __init__.py                 # Addon registration, bl_info dict
├── operators.py                # All operators (13+ operator classes)
├── preferences.py              # AddonPreferences (ImageMagick path, UI location pref)
├── property_groups.py          # PropertyGroup definitions (or may be split into subdirectory)
├── render_operator.py          # Main MODAL render operator
├── ui_lists.py                 # UIList subclasses for animation/material set lists
├── ui_panels.py                # UI Panel classes for 3D viewport sidebar
├── utils.py                    # General utility functions
├── LICENSE                     # MIT
└── README.md                   # Comprehensive documentation
```

### Tests & CI

- **No test directory exists** — zero unit tests, zero integration tests
- **No CI/CD pipeline** — no GitHub Actions, no tox.ini, no pytest config
- **No linting config** — no flake8, mypy, ruff, or black configuration
- **Author self-assessment:** "This is my first substantial Python project"

---

## 2. Architecture Analysis

### Core Render Pipeline

The render operator (`render_operator.py`) is a **modal operator** — this is critical for understanding automation challenges:

```
User clicks "Start Render"
  → SPRITESHEET_OT_RenderOperator.invoke()
    → Sets up timer, registers modal handler
    → Returns {'RUNNING_MODAL'}

Timer fires repeatedly:
  → modal() callback
    → For each (rotation × animation_set × material_set × frame):
      1. SceneSnapshot saves current state
      2. Apply rotation to objects (Z-axis only)
      3. Assign material set to objects
      4. Set animation frame via context.scene.frame_set()
      5. Fit camera (CameraFitting.py)
      6. bpy.ops.render.render() — single frame
      7. Save rendered image to temp directory
    → After all frames rendered:
      8. Call ImageMagick subprocess to assemble spritesheet
      9. Write JSON metadata
      10. SceneSnapshot restores original state
```

### Key Subsystems

**SceneSnapshot (util/SceneSnapshot.py)**
- Saves and restores: object actions, rotation values, object selections
- Uses Python dicts to store state
- Clean save/restore pattern — this is well-designed and reusable

**CameraFitting (util/CameraFitting.py)**
- Computes bounding box of target objects across animation frames
- Adjusts orthographic camera position and ortho_scale
- Four modes: Fit Each Frame, Fit All Frames, Fit Each Animation Set, Fit Each Rotation
- Uses `obj.matrix_world` and mesh vertex positions — **likely to still work** in modern Blender
- **Potential issue:** May use `obj.bound_box` which changed representation in 4.0

**ImageMagick (util/ImageMagick.py)**
- Locates `magick.exe` (Windows-centric path detection)
- Calls `magick montage` via `subprocess.run()` to stitch frames into grid
- Handles padding to power-of-two sizes
- **This entire module should be replaced** with Pillow (PIL) or Blender's native bpy.types.Image

**Property Groups (property_groups.py)**
- `SpritesheetPropertyGroup` — registered on `bpy.types.Scene`
- Contains sub-groups: `animation_options`, `camera_options`, `material_options`, `rotation_options`, `output_options`
- Uses standard `bpy.props.*` (StringProperty, IntProperty, BoolProperty, CollectionProperty, PointerProperty, EnumProperty)
- **PointerProperty with type= references** need verification for 4.x+ API

### Operators Catalog (operators.py)

| Operator ID | Purpose | Headless Safe? |
|---|---|---|
| `spritesheet.render` | Main render entry point | ⚠️ Modal - needs rework |
| `spritesheet.preview_camera` | Preview camera fitting in viewport | ❌ Needs viewport |
| `spritesheet.play_animation_set` | Play animation set in viewport | ❌ Needs viewport |
| `spritesheet.assign_materials` | Assign material set to scene | ✅ Pure data |
| `spritesheet.add_animation_set` | Add new animation set | ✅ Pure data |
| `spritesheet.remove_animation_set` | Remove animation set | ✅ Pure data |
| `spritesheet.add_action` | Add action to animation set | ✅ Pure data |
| `spritesheet.remove_action` | Remove action from set | ✅ Pure data |
| `spritesheet.add_material_set` | Add material set | ✅ Pure data |
| `spritesheet.remove_material_set` | Remove material set | ✅ Pure data |
| `spritesheet.add_material_mapping` | Add object→material mapping | ✅ Pure data |
| `spritesheet.remove_material_mapping` | Remove mapping | ✅ Pure data |
| `spritesheet.prefs_locate_imagemagick` | Auto-detect ImageMagick | ❌ Remove entirely |

---

## 3. Blender API Compatibility Audit

### Critical Breaking Changes (2.9 → 4.x/5.x)

#### High Risk — Likely Broken

| Issue | Details | Fix Complexity |
|---|---|---|
| **Addon packaging** | Uses `bl_info` dict, not `blender_manifest.toml` | Low — add manifest, adjust imports to relative |
| **EEVEE identifier** | In 4.2: `BLENDER_EEVEE` → `BLENDER_EEVEE_NEXT`. In 5.0: back to `BLENDER_EEVEE` | Low — if referenced at all |
| **Action API (5.0)** | Actions now use channelbags and action slots instead of direct FCurve access. `action.id_root` → `action_slot.target_id_type` | Medium — depends on how deeply the addon inspects actions |
| **`context.screen` access** | `context.screen.is_animation_playing` — may not exist in background mode (`--background`) | Medium — needs conditional check or removal |
| **Face Maps removal (4.0)** | Removed entirely — unlikely to affect this addon but need to verify | Negligible |
| **anim_utils changes (4.0+)** | `anim_utils.bake_action()` parameters changed to dataclass | Low — only if baking is used |

#### Medium Risk — Possibly Broken

| Issue | Details | Fix Complexity |
|---|---|---|
| **bgl module deprecated (3.0+)** | Replaced by `gpu` module — only relevant if any viewport drawing is done | Low-Med |
| **Shader node renames (4.0)** | Built-in shader name prefix changes (removed `2D_`/`3D_` prefix) | N/A unless materials are programmatically created |
| **IDProperty typing (4.2)** | IDProperties now have fixed static types | Low — may affect property group edge cases |
| **Object.bound_box** | Representation may have changed — used in CameraFitting | Medium — needs testing |
| **Collection/ViewLayer changes** | Minor API shuffles across versions | Low |

#### Low Risk — Probably Fine

| Issue | Details |
|---|---|
| `bpy.props.*` property definitions | Stable across all versions |
| `bpy.types.Scene` custom properties | Stable |
| `context.scene.frame_set()` | Stable |
| `context.scene.render.fps` | Stable |
| `bpy.ops.render.render()` | Stable |
| `obj.rotation_euler` | Stable |
| `obj.matrix_world` | Stable |
| `context.scene.render.resolution_x/y` | Stable |
| File format settings (PNG, RGBA) | Stable |
| `json` module for metadata output | Standard library — stable |

### Background/Headless Mode Issues

The biggest concern for automation is the **modal operator pattern**:

```python
class SPRITESHEET_OT_RenderOperator(bpy.types.Operator):
    bl_idname = "spritesheet.render"

    def invoke(self, context, event):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # ... render logic per frame ...
```

**This will NOT work in `--background` mode** because:
1. No window manager event loop for timer callbacks
2. No `context.window` to attach timer to
3. Modal handlers require a running GUI event loop
4. `context.screen` doesn't exist in background mode

**Fix:** The render logic needs to be extracted into a synchronous function that can be called directly, bypassing the modal pattern entirely.

---

## 4. Modernization Roadmap

### Phase 1: Fork & Make It Run (Blender 4.2+ / 5.0)
**Estimated effort: 2-3 days**

1. **Create `blender_manifest.toml`** — new extension format metadata
2. **Convert all imports to relative** — `from . import X` instead of absolute
3. **Remove `bl_info`** — replaced by manifest
4. **Audit all `bpy.*` API calls** against 4.2/5.0 changelog
5. **Fix Action API usage** — update any `action.fcurves` / `action.groups` / `action.id_root` calls to use channelbags (5.0) or add version branching
6. **Fix `context.screen` access** — guard with `hasattr` checks or remove viewport-only code paths
7. **Test in Blender 5.0** with a simple model + animation

### Phase 2: Remove ImageMagick Dependency
**Estimated effort: 1-2 days**

Replace `util/ImageMagick.py` entirely with Python-native spritesheet assembly:

```python
# Using Pillow (available in Blender's Python via pip)
from PIL import Image
import math

def assemble_spritesheet(frame_paths, sprite_width, sprite_height, columns=None, pad_to_pot=False):
    frames = [Image.open(p) for p in frame_paths]
    num_frames = len(frames)

    if columns is None:
        columns = math.ceil(math.sqrt(num_frames))
    rows = math.ceil(num_frames / columns)

    sheet_w = columns * sprite_width
    sheet_h = rows * sprite_height

    if pad_to_pot:
        sheet_w = next_power_of_two(sheet_w)
        sheet_h = next_power_of_two(sheet_h)

    sheet = Image.new('RGBA', (sheet_w, sheet_h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        x = (i % columns) * sprite_width
        y = (i // columns) * sprite_height
        sheet.paste(frame, (x, y))

    return sheet
```

Alternatively, use **Blender's native `bpy.types.Image`** API to avoid any external dependency:
```python
# Pure bpy approach — no pip install needed
img = bpy.data.images.new("spritesheet", width=sheet_w, height=sheet_h, alpha=True)
# ... composite pixels from rendered frames ...
img.save_render(output_path)
```

### Phase 3: Add Headless Batch Automation
**Estimated effort: 2-3 days**

1. **Extract render logic from modal operator** into a synchronous `render_spritesheet(config)` function
2. **Create config file parser** (TOML format to match Gloaming ecosystem):

```toml
[output]
directory = "./sprites"
sprite_width = 128
sprite_height = 128
pad_to_power_of_two = true
format = "png"

[[jobs]]
model = "models/character.glb"
render_engine = "EEVEE"

[jobs.camera]
type = "ORTHO"
fit_mode = "fit_all_frames"  # fit_each_frame | fit_all_frames | fit_each_animation | fit_each_rotation

[jobs.rotation]
enabled = true
count = 8            # 8 angles (0, 45, 90, ... 315)
axis = "Z"

[[jobs.animations]]
name = "idle"
action = "Idle"
frame_rate = 12

[[jobs.animations]]
name = "walk"
action = "Walk"
frame_rate = 12

[[jobs.animations]]
name = "attack"
action = "Attack"
frame_rate = 16

[[jobs.materials]]
role = "albedo"
# uses model's default materials

[[jobs.materials]]
role = "normal"
material = "NormalMapMaterial"  # pre-configured material in .blend or library
```

3. **Create batch runner script** (`batch_render.py`):

```python
#!/usr/bin/env python3
"""Run via: blender --background --python batch_render.py -- config.toml"""
import sys
import bpy
import tomllib  # Python 3.11+ (Blender 4.2+)

def main():
    argv = sys.argv
    toml_path = argv[argv.index("--") + 1]

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    for job in config["jobs"]:
        # Import model
        bpy.ops.wm.open_mainfile(filepath=job["model"])
        # or bpy.ops.import_scene.gltf(filepath=job["model"])

        # Configure and render synchronously
        render_spritesheet(job, config["output"])

if __name__ == "__main__":
    main()
```

4. **Invocation:**
```bash
blender --background --python batch_render.py -- sprites_config.toml
```

### Phase 4: Add Test Infrastructure
**Estimated effort: 2-3 days**

#### Testing Strategy

Blender addon testing is uniquely challenging because:
- Tests must run inside Blender's Python environment
- `bpy` is only available when Blender is running
- Most operations require a valid `context`

**Recommended approach:** Use Blender's `--background --python` to run test scripts.

```
tests/
├── conftest.py              # Shared fixtures (create test scenes, cameras, etc.)
├── test_camera_fitting.py   # Unit tests for CameraFitting logic
├── test_scene_snapshot.py   # Unit tests for save/restore
├── test_spritesheet_assembly.py  # Unit tests for image stitching (no bpy needed)
├── test_config_parser.py    # Unit tests for TOML config parsing (no bpy needed)
├── test_render_integration.py    # Integration: render a simple cube, verify output
├── test_animation_render.py      # Integration: animated model → spritesheet
├── test_rotation_render.py       # Integration: multi-angle → spritesheet
├── test_material_sets.py         # Integration: multi-material → separate sheets
├── test_json_metadata.py         # Verify JSON output structure and values
├── fixtures/
│   ├── test_cube.blend           # Simple cube with animation
│   ├── test_character.blend      # Rigged character with walk/idle actions
│   └── test_materials.blend      # Model with normal map material setup
└── run_tests.py             # Test runner that invokes blender --background
```

**Test runner (`run_tests.py`):**
```python
#!/usr/bin/env python3
"""Run all tests: python run_tests.py [--blender /path/to/blender]"""
import subprocess
import sys
import glob

blender = sys.argv[2] if len(sys.argv) > 2 else "blender"
test_files = sorted(glob.glob("tests/test_*.py"))
failures = []

for test_file in test_files:
    print(f"\n{'='*60}\nRunning {test_file}\n{'='*60}")
    result = subprocess.run(
        [blender, "--background", "--python", test_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        failures.append(test_file)
        print(f"FAILED: {test_file}")
        print(result.stderr)
    else:
        print(f"PASSED: {test_file}")

if failures:
    print(f"\n{len(failures)} test(s) failed: {failures}")
    sys.exit(1)
print(f"\nAll {len(test_files)} tests passed.")
```

**Pure Python tests** (spritesheet assembly, config parsing, JSON validation) can use standard pytest without Blender.

**GitHub Actions CI:**
```yaml
name: Test Spritesheet Renderer
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Blender
        run: |
          sudo snap install blender --classic
      - name: Install Python deps
        run: |
          blender --background --python-expr "import subprocess; subprocess.check_call(['pip', 'install', 'Pillow', '--break-system-packages'])"
      - name: Run pure Python tests
        run: pytest tests/test_spritesheet_assembly.py tests/test_config_parser.py tests/test_json_metadata.py
      - name: Run Blender integration tests
        run: python tests/run_tests.py --blender blender
```

### Phase 5: New Features for Gloaming
**Estimated effort: 3-5 days**

1. **Multi-axis rotation** — remove Z-only limitation, support arbitrary azimuth/elevation
2. **glTF/GLB direct import** — auto-import models without pre-configured .blend files
3. **NLA support** — use NLA tracks instead of just actions
4. **Configurable output path** — currently hardcoded alongside .blend file
5. **Post-processing hooks** — run user-defined scripts on output sheets (palette quantization, outline generation, downscaling)
6. **Atlas descriptor formats** — JSON (current), but also Aseprite, TexturePacker, and a Gloaming-native format
7. **Normal map auto-generation** — auto-create a normal map material from the model's geometry and render it as a separate sheet

---

## 5. Effort Summary

| Phase | Work | Days | Priority |
|---|---|---|---|
| Phase 1: Port to Blender 5.0 | API fixes, manifest, relative imports | 2-3 | **P0** |
| Phase 2: Remove ImageMagick | Replace with Pillow/native | 1-2 | **P0** |
| Phase 3: Headless batch automation | Extract from modal, TOML config, CLI | 2-3 | **P0** |
| Phase 4: Test infrastructure | Test framework, fixtures, CI | 2-3 | **P1** |
| Phase 5: Gloaming features | Multi-axis, glTF import, NLA, post-proc | 3-5 | **P2** |
| **Total** | | **10-16 days** | |

## 6. Recommendation

**Fork it.** The core rendering logic (camera fitting, animation stepping, rotation iteration, material swapping, scene snapshot/restore) represents the hardest 60% of the work and it's already done. The ImageMagick dependency and modal operator pattern are the two biggest problems, but both are straightforward to replace.

The author explicitly designed for scripted use (`spritesheet.render` operator, exposed property groups) and chose MIT license — this is a clean foundation.

The fork should be restructured as a **dual-purpose tool**: a Blender extension (for people who want the UI) and a headless CLI pipeline (for automation like your use case). The TOML config approach keeps it consistent with the Gloaming ecosystem and enables CI-driven sprite generation.
