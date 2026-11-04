# Brand family

Theseus and Ariadne are two tools from one story: he crossed the sea to the labyrinth, and her thread led him back out. They come from the same maker as OnePedigree and OneTaxonomy and follow the same structure (`brand/` masters, one small-size icon, one shared interface). This file is identical in both repositories; change it in both.

## App icon

| | Theseus | Ariadne |
| --- | --- | --- |
| Tile gradient (top to bottom) | `#17395a` to `#0c2540` (Aegean blue) | `#a2341f` to `#751f14` (Minoan red ochre) |
| Glyph | A Greek key unwinding into one straight line: the way through, cleared | The classical labyrinth of Knossos, grown from the ancient seed of a cross and four dots |

Shared by both:

- Tile: 896 × 896 on a 1024 canvas, corner radius 200, vertical gradient.
- Glyph: one continuous cream `#fbf8f2` line, round caps and joins, no fill.
- Small sizes (16–32 px): `brand/icon-small.svg`, a larger tile and heavier lines. From 64 px up, the full icon.
- Menu bar: `brand/menu-bar.svg`, the glyph alone, used as a template image so macOS colors it.
- Masters: `brand/icon.svg` (source) and `brand/icon-1024.png` (transparent, for `tauri icon`).

## Interface

`apps/desktop/src/ui/family.css` and `Icon.tsx` are identical in both repositories. Each app sets only `--accent` and `--accent-soft`. They use the same backbone as OnePedigree and OneTaxonomy:

- **Icons**: 24 × 24 line icons drawn from Lucide (ISC), 1.75 stroke, round caps and joins, `currentColor`.
- **Controls**: 32 px buttons, radius 8, 1 px border. Focus ring 2 px orange `#cf8137` (`#e7a066` in dark mode).
- **Cards and panels**: radius 10 with a soft shadow.
- **Color**: warm neutrals around a deep brown and cream. The app's accent marks the current place and the main action. Green, amber and red only ever mean a status.
- **Layout**: a sidebar for the app's few places, one page of cards, and a title that says what you're looking at.
- **Words**: say what happened and what to do next, in plain language.
