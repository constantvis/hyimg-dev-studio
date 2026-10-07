# Hyimg Dev studio

A plugin for [Hyimg](https://github.com/constantvis/Hyimg). It puts HTML files of your library on the board as cards and adds Dev mode, where you work on a page the way you work on a frame in Figma: its DOM tree on the left, the live page in the middle, the selected element's controls, box, styles and attributes on the right. What you change goes into the `.html` file itself. [Русская версия](README.ru.md).

## HTML cards

With the plugin installed, `.html` and `.htm` files show up in the library as kind HTML. Their picture is the page's first screen at 1280 × 800, drawn by Chromium with the page's scripts run. Hyimg keeps it with its thumbnails, never beside the page. Drag a file onto the board and you get a card of that shape.

When a card is big on screen (360 px wide or more) the page itself runs in it, at most four cards at a time and never while you pan or zoom. On a board of 24 cards with four pages running, panning in headless Chromium took the same 16.7 ms per frame as with no pages running. A heavy page will cost more than the test page did.

Every page runs in `<iframe sandbox="allow-scripts">` without `allow-same-origin`. It gets an opaque origin, so it can't read the board, the app's storage or its API. Hyimg serves it from `/sandbox/<key>/<library path>`, and the page's CSS, scripts, fonts and pictures load from there by relative links.

## Dev mode

Double-click an HTML card, or select it and pick **Dev** in the switch at the left of the dock. The card turns live in place and the camera brings it between two panels.

On the left is the tree of the page's elements, with the library's «Find folder» search on top. The search keeps the matching rows and the rows they sit in. Hover a row and its element is marked in the page. Click it and the element opens in the inspector, and the page scrolls to it if it's off screen. Right-click a row to give it one of the board notes' colours: a stripe on its left marks it. The colour is kept on the card (`treeColors` in its board item, keyed by the row's place in the page), not in the page, and the board's ⌘Z takes it back.

**Select** in the dock is on when Dev mode opens. A click in the page selects the element under the pointer, ⇧-click adds one or takes it away, and hovering outlines what a click would take. The page never gets those clicks. Turn Select off (I) when you want to press the page's own buttons.

The tree follows the page: if a script adds rows, the tree shows them within a second. Esc steps out: first the selection, then Dev mode. **Done** in the dock or **Board** in the switch closes it and puts the camera back. ⌘. hides the panels together with the rest of the interface.

## Editing

Since 0.2 the inspector edits the selected elements: Layout (width and height when the page sets them, padding, the gap of a flex or grid box), Appearance (opacity, corners), Fill, Text (colour, size, weight) and Stroke (colour, width). A colour opens the system colour picker, or you type any CSS colour into its field. The change shows in the page at once and lands in the file half a second after you stop. With several elements selected, every one of them gets it.

When a value comes from a custom property, say `background: var(--purple)` with `--purple` declared in `:root`, the inspector names the property and asks: **This element** writes the colour into this element only, **Everywhere · 3** changes the declaration, so its 3 uses in the file follow.

Double-click a text, or press Enter with it selected, to type it in place. Enter, Esc or a click elsewhere applies it, as with the board's notes. Only an element that holds nothing but text can be typed.

How it writes. The server sends the page its own source with every start tag marked by its offset. The page parses that copy with the browser's own parser and pairs it with the live tree, so each element you select knows its tag in the file. An edit changes only that tag's `style` attribute, the text between its tags, or the one `:root` declaration. Every other byte of the file stays as it was. The file's revision is checked on every write: if someone else changed the file meanwhile, the page reads it again first.

What can't be saved, with the controls grey and the reason above them:

- an element a script of the page made: the file has no such element
- a tag the browser added by itself (a `tbody`, an `html` or `body` the file never wrote)
- a custom property declared in a linked stylesheet or inside `@media`: «Everywhere» is off for it, «This element» still works.

Each write is one step of ⌘Z and ⇧⌘Z while Dev mode is open (the buttons are in the dock too). A step is undone only if the file is still as that step left it. Before the first write of each Dev mode session Hyimg keeps a copy of the file in the board's history, `boards/_history/_html/<library path>/<time>.html` with a line in `index.jsonl`, and every write is logged with who made it. When you leave Dev mode the card's picture is drawn again from the new file.

The page still runs sandboxed. The edits are made by the board, through `POST /api/plugin/dev/edit`, which takes only `.html` and `.htm` files inside the library and only these edits. A sandboxed page sends `Origin: null`, and Hyimg refuses its writes.

The frames plugin's HTML frames open in Dev mode too, by a double-click or the switch, as long as their live view isn't open. The frame's live view (device sizes, edges that resize the page) stays one click away: **Live view** in Dev mode's dock, or on the bar over the selected frame. With this plugin turned off in Settings › Plugins, a double-click on a frame opens its live view as before, and the HTML cards stay on the board as their pictures, marked «Plugin off».

## Comments and drawings

**Comment** (C) in Dev mode's dock pins a comment thread of Hyimg's board to an element of the page: a click in the page picks the element under it. The thread keeps the element's place in the tree (`html>body:1>main:1>section:0>h1:0`), a CSS selector (`#t`), its tag and text, and the point in the page. In Dev mode the pin stands on the element and follows it when the page scrolls; on the board it stands at that point of the card's picture. **Draw** (P) is the board's Annotate over the page, anchored to the card. Agents read the threads with `hy.py comments`, which names the element.

## Install

The plugin runs inside [Hyimg](https://github.com/constantvis/Hyimg). The simplest way is Hyimg's script: it puts this repository beside `hyimg` and links it:

```sh
cd hyimg && ./scripts/install_plugins.sh --dev
```

Or by hand: clone this repository and run `ln -s <path to hyimg-dev-studio> ~/Library/Application\ Support/Hyimg/plugins/dev`, then View › Restart server (⇧⌘R) in Hyimg. It needs a Hyimg with the mode switch and `/sandbox/` (October 2026 or later). For the pictures of pages it needs Playwright with Chromium (`python3 -m pip install playwright && python3 -m playwright install chromium`). Without it Quick Look draws the page without its scripts.

**For agents:** don't install the plugin silently. Ask the person whether they want Dev studio (HTML pages as cards on the board, edited in place like a frame in Figma), and install only after a yes.

## Tests

```sh
HYIMG_REPO=<hyimg checkout> python3 -m pytest tests/test_dev_studio.py tests/test_dev_edit.py
python3 -m pytest tests/unit && node --test tests/unit/js/
```

**For agents changing the code:** a source file stays around 1000 lines (the check fails above 1100) and a line around 160 characters (fails above 200). A file near the limit is split by responsibility, one concern per module. The rule and its exceptions are in Hyimg's `AGENTS.md`, section «Размер файлов». `scripts/check.sh --fast` in `hyimg` checks this repository too.

## License

[PolyForm Noncommercial 1.0.0](LICENSE): free to use, study and change for yourself and for noncommercial purposes. Commercial use only with the author's permission.
