# Brand family

Theseus and Ariadne are two tools from one story: he crossed the sea to the labyrinth, and her thread led him back out. They come from the same maker as OnePedigree and OneTaxonomy and follow the same structure (`brand/` masters, one small-size icon, one shared interface). This file is identical in both repositories; change it in both. What the two apps promise and how they stay in step is in `MANIFESTO.md`.

## App icon

| | Theseus | Ariadne |
| --- | --- | --- |
| Tile gradient (top to bottom) | `#cfe9e6` to `#97cfc9` (seafoam) | `#f6d5de` to `#e8a3b7` (rose) |
| Glyph | A compass with an upright needle: finding your way | A spool of thread: everything can find its way back |

Shared by both:

- Tile: 896 × 896 on a 1024 canvas, corner radius 200, vertical pastel gradient, the same soft family as OnePedigree's and OneTaxonomy's.
- Glyph: a simple drawing in deep brown `#4c312c` line, round caps and joins, no fill. It stays broad, so neither app is tied to one idea of what it does.
- Small sizes (16–32 px): `brand/icon-small.svg`, a larger tile, heavier lines and a simpler glyph. From 64 px up, the full icon.
- Menu bar: `brand/menu-bar.svg`, the glyph alone, used as a template image so macOS colors it.
- Masters: `brand/icon.svg` (source) and `brand/icon-1024.png` (transparent, for `tauri icon`).

## Interface

`apps/desktop/src/ui/family.css` and `Icon.tsx` are identical in both repositories. Each app sets only `--accent` and `--accent-soft`. They use the same backbone as OnePedigree and OneTaxonomy:

- **Icons**: 24 × 24 line icons drawn from Lucide (ISC), 1.75 stroke, round caps and joins, `currentColor`.
- **Controls**: 32 px buttons, radius 8, 1 px border. Focus ring 2 px orange `#cf8137` (`#e7a066` in dark mode).
- **Cards and panels**: radius 10 with a soft shadow.
- **Color**: warm neutrals around a deep brown and cream. The app's accent marks the current place and the main action: a deep teal in Theseus, a deep rose in Ariadne, so text and buttons stay readable. Green, amber and red only ever mean a status.
- **Emoji**: none on screen; line icons do that job. The engine's emoji are for the phone note, where icons aren't possible.
- **Editing**: saved as you go, with undo and redo. Drag rows with `ui/useDrag.ts`. A check-off waits three seconds before it moves anything.
- **Layout**: a sidebar for the app's few places, one page of cards, and a title that says what you're looking at.
- **Words**: say what happened and what to do next, in plain language.
