# Forge3D Item Factory

Forge3D is a completely free, offline-first Windows pipeline for procedural game items. The included starter builds **Aegis-01**, a futuristic football helmet, using Blender's built-in Python API.

The hosted web interface is a configurator and script generator. The local Windows kit can launch Blender, render colorways, run QA, and export the finished asset pack. No account, paid API, subscription, API key, or cloud runtime is required for any core feature.

## What it creates

Each local build writes:

- an editable `.blend` scene with named objects and modifiers;
- a game-friendly `.glb` export;
- an `.fbx` interchange export;
- one PNG preview for every colorway;
- the exact JSON recipe used for the build;
- a `qa_report.json` with triangle count, dimensions, topology observations, materials, and budget checks;
- a build manifest and Blender log.

## Windows quick start

1. Install [Python 3](https://www.python.org/downloads/windows/) and [Blender](https://www.blender.org/download/). Both are free.
2. Download and unzip `forge3d-windows-starter.zip`.
3. Double-click `start-forge3d.bat`.
4. Your browser opens `http://127.0.0.1:8787`. Choose a recipe and select **Build with local Blender**.
5. Download the generated files from the finished build, or open the kit's `output` folder.

The local server binds only to `127.0.0.1`. It uses Python's standard library, has no package-install step, and does not upload your prompts or models.

If Blender is installed somewhere unusual, set its path before starting:

```bat
set FORGE3D_BLENDER=D:\Apps\Blender\blender.exe
start-forge3d.bat
```

## Direct Blender build

Double-click `build-helmet.bat`, or use Blender from a terminal:

```powershell
blender --background `
  --python blender\forge3d_item_factory.py `
  -- --recipe presets\futuristic_football_helmet.json `
  --output output\helmet
```

Open the script directly in Blender's Scripting workspace if you prefer to inspect and run every step interactively.

## Import a downloaded model

Forge3D can merge a model you obtained from Meshy or any other source without contacting that service. Export or download a `.glb`, `.gltf`, `.fbx`, or `.obj`, then either:

- paste the full local file path into the web interface's **Merge an external model** field; or
- run the engine with `--import-model "C:\path\to\model.glb"`.

The imported objects are moved into the editable `MODEL` collection and included in QA and exports. You are responsible for the source model's license and usage rights.

## Project map

```text
.
├── blender/forge3d_item_factory.py  # procedural model, materials, QA, exports
├── dist/                            # static hosted/offline web interface
├── presets/                         # editable JSON recipes
├── tests/                           # no-dependency checks
├── local_server.py                  # localhost bridge to Blender
├── start-forge3d.bat                # Windows web launcher
└── build-helmet.bat                 # direct background build
```

## Honest scope

The browser uses transparent rule-based prompt parsing; it is not pretending to be a generative AI service. The first production template is the futuristic football helmet. New item families are added by implementing another procedural builder and registering its explicit parameters. This keeps generation deterministic, inspectable, and free.

The concept preview in the browser is a fast 2.5D visualization. Blender creates the actual 3D geometry and final renders.

## Automated checks

Run the tests from the repository root:

```powershell
python -m py_compile blender\forge3d_item_factory.py local_server.py
node tests\test-generator.cjs
python tests\verify_static.py
```

Blender itself is required for a full geometry/render/export integration test.

## License

The project is released under [CC0 1.0](LICENSE). You may use, modify, redistribute, and sell your modifications without asking permission. Blender and any imported models retain their own licenses.
