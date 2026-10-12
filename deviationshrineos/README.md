# DeviationShrineOS

A buildless browser desktop combining the 640×480, 16-color, bitmap aesthetic of TempleOS with the Strange Anchor. Published as an owner-private Site.

Open `dist/index.html` through any static HTTP server. There are no runtime dependencies, network APIs, model calls, or remote fonts.

The desktop includes draggable, minimizable, maximizable windows; a local random-fragment shrine; a clickable ship atlas; eight crew records with source links; a command shell; an autosaving logbook; and a bounded drawing language with seven commands. The geometry remains 4:3 in fit, 1×, 2×, and fullscreen modes.

## Source structure

- `dist/app.js`: application state, windows, input, local persistence, and program content.
- `dist/core.js`: pure command parsing and random composition.
- `dist/graphics.js`: pixel line rasterization and procedural graphics.
- `dist/style.css`: 16-color desktop and responsive display housing.
- `dist/assets/shrine-vga.woff`: vector conversion of TempleOS's original 8×8 bitmap table.
- `dist/assets/font-bitmap.json`: the public-domain source glyph data.

`npm test` checks the interpreter and shell grammar. A separate DOM interaction pass exercises windows, log persistence, the oracle, and drawing using a simulated DOM; it is not visual browser QA.

## Boundary

This is an interface simulation, not an x86 emulator, bootable operating system, or HolyC compiler. DriftC deliberately accepts only one whitelisted command per line, parses string literals as JSON, never evaluates JavaScript, and limits program length, operation count, and drawing coordinates. All visible instrument movement is illustrative. Shrine outputs are chance compositions, not predictions or context-sensitive model responses.

Notes and code are saved in browser localStorage under `deviationshrineos.0137`. Export buttons produce plain-text copies. A display reboot keeps both files. If storage is blocked or full, the app keeps the session in memory and explains how to export.

## Attribution

TempleOS: Terry A. Davis. TempleOS and its font table are public domain. The official archive identifies the original font source as FreeDOS. Font source: https://templeos.info/Wb/Kernel/FontStd.HC.HTML

Strange Anchor: https://strangeanchor.khazars.wiki/index.html and linked crew plates. Specific links are included in the app's Ship's Papers and crew records. Crew summaries are condensed from these pages; terminal asides, the schematic, and oracle fragments are original adaptations created for this site.

Original pixel artwork is generated directly in canvas code. ASCII crew-name spellings preserve the original font's character set.
