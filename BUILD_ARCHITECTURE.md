# Pixell Agent Kit - Build Process Architecture

## ASCII Diagram: Build Process Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PIXELL BUILD SYSTEM                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │ pixell build │
                            │   (CLI)      │
                            └──────┬───────┘
                                   │
                                   v
                    ┌──────────────────────────┐
                    │   AgentBuilder.build()   │
                    │  (core/builder.py:31)    │
                    └──────────┬───────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                              │
                v                              v
    ┌──────────────────┐          ┌──────────────────────┐
    │   VALIDATION     │          │  LOAD agent.yaml     │
    │  AgentValidator  │          │  AgentManifest model │
    └──────────────────┘          └──────┬───────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │    Create Temporary Build Directory       │
                    └─────────────────────┬─────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                  │
        v                                 v                                  v
┌──────────────┐             ┌──────────────────────┐         ┌──────────────────┐
│ Copy Agent   │             │ Create Metadata      │         │ Generate setup.py│
│ Files        │             │ .pixell/package.json │         │ (pip install)    │
│ - src/       │             └──────────────────────┘         └──────────────────┘
│ - agent.yaml │
│ - .env       │                        │
│ - README.md  │                        v
└──────────────┘             ┌──────────────────────┐
                             │ Create requirements  │
                             │ (if not present)     │
                             └──────────────────────┘
                                          │
                                          v
        ┌─────────────────────────────────────────────────────────────┐
        │           _create_dist_layout() - SURFACE BUILDING          │
        │                  (builder.py:437-471)                       │
        └─────────────────────────────────────────────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                  │
        v                                 v                                  v
┌─────────────────┐          ┌─────────────────────┐         ┌─────────────────────┐
│   A2A Surface   │          │   REST Surface      │         │    UI Surface       │
│  (if configured)│          │  (if configured)    │         │  (if configured)    │
└─────────────────┘          └─────────────────────┘         └─────────────────────┘
        │                                │                                  │
        v                                v                                  v
┌─────────────────┐          ┌─────────────────────┐         ┌─────────────────────┐
│ Parse a2a field:│          │ Parse rest field:   │         │ Parse ui field:     │
│ a2a:            │          │ rest:               │         │ ui:                 │
│   service:      │          │   entry:            │         │   path: ui          │
│   src.a2a.      │          │   src.rest.index:   │         └──────────┬──────────┘
│   server:serve  │          │   mount             │                    │
└────────┬────────┘          └──────────┬──────────┘                    v
         │                              │                  ┌──────────────────────────┐
         v                              v                  │ Get UI source directory  │
┌──────────────────┐        ┌──────────────────────┐      │ project_dir / "ui"       │
│ Convert module   │        │ Convert module path  │      └──────────┬───────────────┘
│ to file path:    │        │ to file path:        │                 │
│ src.a2a.server → │        │ src.rest.index →     │                 v
│ src/a2a/server.py│        │ src/rest/index.py    │      ┌──────────────────────────┐
└────────┬─────────┘        └──────────┬───────────┘      │ shutil.copytree()        │
         │                              │                  │ Copy ENTIRE directory    │
         v                              v                  │ ui/ → dist/ui/           │
┌──────────────────┐        ┌──────────────────────┐      │ - index.html             │
│ shutil.copy2()   │        │ shutil.copy2()       │      │ - styles.css             │
│ Copy single file │        │ Copy single file     │      │ - app.js                 │
│ src/a2a/server.py│        │ src/rest/index.py →  │      │ - assets/*               │
│ → dist/a2a/      │        │ → dist/rest/         │      └──────────────────────────┘
└──────────────────┘        └──────────────────────┘
        │                              │                                  │
        └──────────────────────────────┴──────────────────────────────────┘
                                       │
                                       v
                        ┌──────────────────────────┐
                        │  Create deploy.json      │
                        │  {                       │
                        │    "expose": [           │
                        │      "a2a", "rest", "ui" │
                        │    ],                    │
                        │    "ports": {            │
                        │      "a2a": 50051,       │
                        │      "rest": 8080,       │
                        │      "ui": 3000          │
                        │    },                    │
                        │    "multiplex": true     │
                        │  }                       │
                        └──────────┬───────────────┘
                                   │
                                   v
                        ┌──────────────────────────┐
                        │  Create ZIP Archive      │
                        │  _create_apkg()          │
                        │  (builder.py:500-522)    │
                        │                          │
                        │  Zip entire temp dir →   │
                        │  {name}-{version}.apkg   │
                        └──────────┬───────────────┘
                                   │
                                   v
                        ┌──────────────────────────┐
                        │   OUTPUT                 │
                        │ test-agent-0.1.0.apkg    │
                        │   (ZIP file)             │
                        └──────────────────────────┘
```

## Key Components

### Build Entry Points
- **CLI**: `pixell/cli/main.py:182-213`
- **Core Builder**: `pixell/core/builder.py:31-90`

### Surface Building
- **A2A Component**: `pixell/core/builder.py:446-453`
  - Copies single Python file for gRPC server
  - Port: 50051

- **REST Component**: `pixell/core/builder.py:455-462`
  - Copies entry module for FastAPI
  - Port: 8080

- **UI Component**: `pixell/core/builder.py:464-471`
  - Copies entire static directory
  - Port: 3000

### Metadata Files
- **deploy.json**: Deployment configuration with exposed surfaces and ports
- **.pixell/package.json**: Package metadata and manifest
- **setup.py**: Auto-generated Python package installer

## Build Process Summary

1. **Validation**: Check manifest and required files
2. **Manifest Loading**: Parse agent.yaml with Pydantic models
3. **File Assembly**: Copy source files to temporary directory
4. **Surface Building**: Create dist/ layout for A2A, REST, and UI components
5. **Metadata Generation**: Create deploy.json and package metadata
6. **APKG Creation**: Zip entire structure into .apkg file

## Key Differences: Component Building

| Aspect | A2A | REST | UI |
|--------|-----|------|-----|
| **Copy Method** | `shutil.copy2()` | `shutil.copy2()` | `shutil.copytree()` |
| **Source Type** | Single file | Single file | Entire directory |
| **Protocol** | gRPC | HTTP/REST | HTTP/Static |
| **Port** | 50051 | 8080 | 3000 |
