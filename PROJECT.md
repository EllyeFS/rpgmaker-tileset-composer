# RPG Maker MZ Tileset Composer

A standalone desktop application to visually compose RPG Maker MZ tilesets by selecting and arranging tiles from multiple source images.

---

## Problem Statement

RPG Maker MZ uses a specific tileset format where each tileset is composed of multiple image files (A1-A5, B-E), each with strict dimension requirements. Game developers often need to:

- Combine tiles from different tileset packs into a single cohesive tileset
- Replace specific tiles while keeping others
- Create custom tilesets by cherry-picking from various sources

The current workflow involves manually opening image editors (GIMP, Photoshop), calculating tile positions, and copy-pasting individual tiles — a tedious and error-prone process.

**This application provides a visual, drag-and-drop interface to compose tilesets efficiently.**

---

## RPG Maker MZ Tileset Format

All tiles are **48×48 pixels**. Tilesets are organized into specific image files:

### Tileset Types and Dimensions

| Type | Dimensions | Grid Size | Purpose | Layer |
|------|------------|-----------|---------|-------|
| **A1** | 768×576 | Special | Animated tiles (water, waterfalls) | Lower |
| **A2** | 768×576 | Special | Ground autotiles | Lower |
| **A3** | 768×384 | 16×8 tiles | Building autotiles | Lower |
| **A4** | 768×720 | Special | Wall autotiles | Lower |
| **A5** | 384×768 | 8×16 tiles | Normal tiles | Lower |
| **B** | 768×768 | 16×16 tiles | Normal tiles | Upper |
| **C** | 768×768 | 16×16 tiles | Normal tiles | Upper |
| **D** | 768×768 | 16×16 tiles | Normal tiles | Upper |
| **E** | 768×768 | 16×16 tiles | Normal tiles | Upper |

### Autotile Structure

Autotiles (A1-A4) are **not** individual 48×48 tiles. They are composed of **tile groups** that RPG Maker uses to automatically generate boundary variations. The most common autotile pattern is a **2×3 block (96×144 pixels)**.

#### A1 (Animated Autotiles) — 768×576

4 rows with alternating animated and static autotile units:

```
┌─────────────────────────────────────────────────────────────────┐
│ [Animated 6×3] [Static 2×3] [Animated 6×3] [Static 2×3]  Row 1  │
│ [Animated 6×3] [Static 2×3] [Animated 6×3] [Static 2×3]  Row 2  │
│ [Animated 6×3] [Static 2×3] [Animated 6×3] [Static 2×3]  Row 3  │
│ [Animated 6×3] [Static 2×3] [Animated 6×3] [Static 2×3]  Row 4  │
└─────────────────────────────────────────────────────────────────┘
```

- **Animated autotile**: 6×3 tiles (288×144 px) — contains 3 animation frames of 2×3 each
- **Static autotile**: 2×3 tiles (96×144 px) — can be decoration overlay or waterfall
- Row width: 288 + 96 + 288 + 96 = 768 px
- Total: 8 animated units + 8 static units = **16 units**

#### A2 (Ground Autotiles) — 768×576

4 rows, each containing 2 blocks (A and B):

```
┌─────────────────────────────────────┐
│ Row 1: Block A (4 autotiles) + Block B (4 autotiles) │
│ Row 2: Block A (4 autotiles) + Block B (4 autotiles) │
│ Row 3: Block A (4 autotiles) + Block B (4 autotiles) │
│ Row 4: Block A (4 autotiles) + Block B (4 autotiles) │
└─────────────────────────────────────┘
```

- Each autotile unit: **2×3 tiles (96×144 px)**
- 8 autotile units per row, 4 rows = 32 total autotile units

#### A3 (Building Autotiles) — 768×384

Simpler structure using only the "group pattern" (no full autotile boundaries):

- Grid: **16×8 individual tiles**
- Each autotile unit: **2×2 tiles (96×96 px)**
- 8 columns × 4 rows = 32 autotile units

#### A4 (Wall Autotiles) — 768×720

Alternating rows of different autotile types:

```
┌─────────────────────────────────────┐
│ Row 1-3: Wall tops (2×3 each, 8 units)              │
│ Row 4-5: Wall faces (2×2 each, 8 units)             │
│ Row 6-8: Wall tops (2×3 each, 8 units)              │
│ Row 9-10: Wall faces (2×2 each, 8 units)            │
│ ... pattern repeats 3× total ...                    │
└─────────────────────────────────────┘
```

- Wall tops: 2×3 (96×144 px) — 8 units × 3 groups = 24 units
- Wall faces: 2×2 (96×96 px) — 8 units × 3 groups = 24 units
- Total: 48 autotile units

#### A5 (Normal Tiles) — 384×768

**Simple grid — no autotile behavior.**

- Grid: **8×16 individual 48×48 tiles**
- Each tile is independent
- Total: 128 tiles

#### B, C, D, E (Upper Layer Tiles) — 768×768 each

**Simple grid — no autotile behavior.**

- Grid: **16×16 individual 48×48 tiles**
- Each tile is independent
- Total: 256 tiles per sheet
- B/C/D/E are functionally interchangeable
- **Note:** Top-left tile of B should be empty/transparent (represents "no tile")

---

## Application Design

### Core Workflow

1. **Configure Source Folders**
   - User points to folders containing source tileset images
   - One folder per tileset type (or auto-detect by dimensions)
   - Application indexes all available tiles/autotile-units

2. **Select Target Type**
   - User chooses which tileset file to create (A1, A2, A3, A4, A5, B, C, D, or E)
   - Application displays an empty canvas matching that type's dimensions and grid

3. **Browse Tile Palette**
   - Source tiles displayed as a scrollable palette
   - For autotiles: show the representative pattern (first tile of each unit)
   - Grouped by source file for organization

4. **Compose Tileset**
   - Drag tiles from palette to target canvas
   - Click to select, click to place
   - Visual preview of the composed tileset
   - Ability to clear/replace individual slots

5. **Export**
   - Save the composed tileset as PNG
   - Filename follows RPG Maker conventions

### User Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [File]  [Edit]  [View]  [Help]                    Menu Bar │
├─────────────────────────────────────────────────────────────┤
│  Source Folders: [...]  │  Target: [A5 ▼]  │  [Export PNG]  │
├───────────────────────┬─────────────────────────────────────┤
│                       │                                     │
│   TILE PALETTE        │         TARGET CANVAS               │
│   (scrollable)        │         (matches target type)       │
│                       │                                     │
│   ┌───┬───┬───┬───┐   │         ┌───┬───┬───┬───┬───┐       │
│   │ ■ │ ■ │ ■ │ ■ │   │         │   │   │ ■ │   │   │       │
│   ├───┼───┼───┼───┤   │         ├───┼───┼───┼───┼───┤       │
│   │ ■ │ ■ │ ■ │ ■ │   │         │   │ ■ │ ■ │ ■ │   │       │
│   ├───┼───┼───┼───┤   │         ├───┼───┼───┼───┼───┤       │
│   │ ■ │ ■ │ ■ │ ■ │   │         │   │   │   │   │   │       │
│   └───┴───┴───┴───┘   │         └───┴───┴───┴───┴───┘       │
│                       │                                     │
│   [Source: grass.png] │                                     │
│                       │                                     │
└───────────────────────┴─────────────────────────────────────┘
│  Status: 3/128 tiles placed                                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Drag-and-drop** from palette to canvas
- **Visual grid overlay** showing tile boundaries
- **Zoom controls** for both palette and canvas
- **Undo/Redo** support
- **Save/Load project** (remember source folders + current composition)
- **Clear canvas** / **Clear slot**
- **Duplicate source detection** (warn if same tile placed twice)

---

## Technical Implementation

### Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| GUI Framework | PySide6 (Qt 6) |
| Image Processing | Pillow (PIL) |
| Packaging | PyInstaller |

## Notes and Considerations

### Autotile Unit Sizes Reference

| Type | Unit Size (tiles) | Unit Size (pixels) | Units per Image |
|------|-------------------|-------------------|-----------------|
| A1 (animated) | 6×3 | 288×144 | 8 |
| A1 (static) | 2×3 | 96×144 | 8 |
| A2 | 2×3 | 96×144 | 32 |
| A3 | 2×2 | 96×96 | 32 |
| A4 (wall top) | 2×3 | 96×144 | 24 |
| A4 (wall face) | 2×2 | 96×96 | 24 |
| A5 | 1×1 | 48×48 | 128 |
| B-E | 1×1 | 48×48 | 256 |

### Transparency

- All tileset images use PNG format with alpha channel

---

## References

- [RPG Maker MZ Asset Standards](https://rpgmakerofficial.com/product/MZ_help-en/01_11_01.html)
- RPG Maker MZ ships with example tilesets in `img/tilesets/`
