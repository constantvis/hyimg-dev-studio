# Hyimg Dev Studio

A plugin for [Hyimg](https://github.com/constantvis/Hyimg). It puts HTML files of your library on the board as cards and adds Dev Studio, where you work on a page the way you work on a frame in Figma: its DOM tree on the left, the live page in the middle, the selected element's controls, box, styles and attributes on the right. What you change goes into the `.html` file itself. [Русская версия](README.ru.md).

## HTML cards

With the plugin installed, `.html` and `.htm` files show up in the library as kind HTML. Their picture is the page's first screen at 1280 × 800, drawn by Chromium with the page's scripts run. Hyimg keeps it with its thumbnails, never beside the page. Drag a file onto the board and you get a card of that shape.

The picture is drawn at twice the page's size, 2560 × 1600, and each card asks for the size it needs on screen: 640, 1280 or 2560 px wide, counting the display's pixels. Zoom in and the sharper picture fades in over the blurry one. Zoom out and the card goes back to a small one. A card off screen asks for nothing.

When a card is big on screen (360 px wide or more) the page itself runs in it, at most four cards at a time and never while you pan or zoom. The four go to cards you can see, the selected one first, then the ones nearest the middle of the screen. A card off screen gives its page up as soon as the board stops, and a card that waited gets the page within a quarter of a second. On a board of 24 cards with four pages running, panning in headless Chromium took the same 16.7 ms per frame as with no pages running. A heavy page will cost more than the test page did.

Every page runs in `<iframe sandbox="allow-scripts">` without `allow-same-origin`. It gets an opaque origin, so it can't read the board, the app's storage or its API. Hyimg serves it from `/sandbox/<key>/<library path>`, and the page's CSS, scripts, fonts and pictures load from there by relative links.

## Dev Studio

Double-click an HTML card, or select it and pick **Dev** in the switch at the left of the dock. The card turns live in place and the camera brings it between two panels.

On the left is the tree of the page's elements, with the library's «Find folder» search on top. The search keeps the matching rows and the rows they sit in. Hover a row and its element is marked in the page. Click it and the element opens in the inspector, and the page scrolls to it if it's off screen. Right-click a row to give it one of the board notes' colours: a stripe on its left marks it. The colour is kept on the card (`treeColors` in its board item, keyed by the row's place in the page), not in the page, and the board's ⌘Z takes it back.

Dev Studio opens with the page live: its buttons, links and fields work as in a browser, and **Select** in the dock is off. It opens that way every time, nothing is remembered per card. Press I or click Select to turn it on. Then a click in the page selects the element under the pointer, ⇧-click adds one or takes it away, hovering outlines what a click would take, and a double click types a text in place. The page doesn't get those clicks. Press I again to give them back. I works while the page has the focus too, unless you're typing in one of its fields.

A pinch, or ⌃ or ⌘ with the wheel, over the page zooms the board at the pointer, as over a picture. The page itself doesn't scale. A plain two-finger scroll still scrolls the page. If the page has a zoom of its own (a map, a canvas app), click into it: the zoom goes to the page and the dock says «The page has the zoom · Esc to give it back». Nothing is drawn round the card. Esc, a click outside the card or leaving the studio gives the zoom back to the board. Hold ⌥ while pinching to send that one gesture to the page without clicking. The frames plugin's HTML live view works the same way, since Hyimg does this part (`review/ui/framezoom.js`).

While the studio is open the board's selection outline is gone, so you see the card's edges. The card is lifted instead: a soft shadow under it and the rest of the board slightly darker. Hyimg does this for every studio (`review/ui/editlift.js`).

The tree follows the page: if a script adds rows, the tree shows them within a second. Esc steps out: first the page's zoom if it has it, then the selection, then Dev Studio. **Done** in the dock or **Board** in the switch closes it and puts the camera back. ⌘. hides the panels together with the rest of the interface.

## Editing

Since 0.2 the inspector edits the selected elements: Layout (width and height, «auto» until you type a number, padding, the gap of a flex or grid box), Appearance (opacity, corners, blur), Fill, Text (colour, size, weight) and Stroke (colour, width). A colour opens the system colour picker, or you type any CSS colour into its field. The change shows in the page at once and lands in the file half a second after you stop. With several elements selected, every one of them gets it.

Every number field drags by its label, as in Figma: W, H, Padding, Gap, Corners, Blur, the text's Size and the stroke's Width. Drag the letter left or right and the number follows. Hold ⇧ to go ten times faster, ⌥ to go ten times finer. The page follows the drag, and the file takes the value once, when you let go, so a drag is one step of ⌘Z. Esc during the drag puts the old value back and writes nothing. Click the label without moving to type the number: Enter writes it, Esc puts it back. Padding and stroke width with different sides move every side by the same amount, none below 0. W and H at «auto» start from the element's size in the page. The handle and the controls of the block are Hyimg's shared micro elements (`review/ui/hy`): the Edit mini toggle, the file's light, the «This element | Everywhere» micro segments, the change dot and the row's icons on hover.

When a value comes from a custom property, say `background: var(--purple)` with `--purple` declared in `:root`, the inspector names the property and asks: **This element** writes the colour into this element only, **Everywhere · 3** changes the declaration, so its 3 uses in the file follow.

Double-click a text, or press Enter with it selected, to type it in place. Enter, Esc or a click elsewhere applies it, as with the board's notes. Only an element that holds nothing but text can be typed.

How it writes. The server sends the page its own source with every start tag marked by its offset. The page parses that copy with the browser's own parser and pairs it with the live tree, so each element you select knows its tag in the file. An edit changes only that tag's `style` attribute, the text between its tags, or the one `:root` declaration. Every other byte of the file stays as it was. The file's revision is checked on every write: if someone else changed the file meanwhile, the page reads it again first.

What can't be saved, with the controls grey and the reason above them:

- an element a script of the page made: the file has no such element
- a tag the browser added by itself (a `tbody`, an `html` or `body` the file never wrote)
- a custom property declared in a linked stylesheet or inside `@media`: «Everywhere» is off for it, «This element» still works.

Each write is one step of ⌘Z and ⇧⌘Z while Dev Studio is open (the buttons are in the dock too). A step is undone only if the file is still as that step left it. Before the first write of each Dev Studio session Hyimg keeps a copy of the file in the board's history, `boards/_history/_html/<library path>/<time>.html` with a line in `index.jsonl`, and every write is logged with who made it. When you leave Dev Studio the card's picture is drawn again from the new file.

The page still runs sandboxed. The edits are made by the board, through `POST /api/plugin/dev/edit`, which takes only `.html` and `.htm` files inside the library and only these edits. A sandboxed page sends `Origin: null`, and Hyimg refuses its writes.

The frames plugin's HTML frames open in Dev Studio too, by a double-click or the switch, as long as their live view isn't open. The frame's live view (device sizes, edges that resize the page) stays one click away: **Live view** in Dev Studio's dock, or on the bar over the selected frame. With this plugin turned off in Settings › Plugins, a double-click on a frame opens its live view as before, and the HTML cards stay on the board as their pictures, marked «Plugin off».

## Inspector, History and Edit mode

The right block has two tabs, **Inspector** and **History**, and under them the picked element: its tag, its parent and itself as crumbs (a click on the parent picks it), its size, and a 6 px light for the file. The light is a ring before the first write and when the element can't be saved (its tooltip says which), green once this session wrote to the file, blinking while a write is on its way. History lists this session's writes, the undone ones dimmed, the newest last. A click on one takes the file to the state right after it, **Opened** takes it back to the file as Dev Studio found it.

**Edit** at the right end of the block's header, or E, turns on Edit mode: the HTML is edited the way a browser's inspector edits it (owner 2026-10-09: «как в браузере в инспекторе можно редактировать, так же и тут»). E again goes back to Inspect, the studio as before. Select turns on with Edit mode and goes back to how it was when you leave it.

- In the tree, a double click on a row's tag renames the element, on its #id or .classes edits that attribute, on a leaf's text edits the text. Enter applies, Esc cancels, clicking away applies. Under the pointer a row shows + (type attributes as `name="value"`) and a bin. ⌫ or Delete deletes the selected elements.
- In the inspector, Attributes lists every attribute as a name and a value you can type in, `class` and `style` included. The page follows as you type, Enter or leaving the field writes it, Esc puts it back. × removes an attribute, + adds some.
- In the page, a double click on a text types it, with Select on or off.

A row whose element was written gets a green dot. Each change is one step of ⌘Z, and undoing a delete puts the element back where it stood in the page.

What goes into the file: only the bytes of that change. An attribute's value is written between its own quotes and escaped, a rename changes the start tag's name and the end tag's, a delete takes the element from its start tag to the end of its end tag, and its whole line when nothing else stands on it. The rest of the file stays byte for byte. To find an element's end tag the server counts the same tags nested in it, and it checks that the number of start tags inside matches what the page parsed. When the file leaves an end tag out (an `li` followed by the next `li`) or the browser closes the element somewhere else, the rename or delete is refused with the reason, and nothing is written. `html`, `head` and `body` are never renamed or deleted.

## Comments and drawings

**Comment** (C) in Dev Studio's dock pins a comment thread of Hyimg's board to an element of the page: a click in the page picks the element under it. The thread keeps the element's place in the tree (`html>body:1>main:1>section:0>h1:0`), a CSS selector (`#t`), its tag and text, and the point in the page. In Dev Studio the pin stands on the element and follows it when the page scrolls; on the board it stands at that point of the card's picture. **Draw** (P) is the board's Annotate over the page, anchored to the card. Agents read the threads with `hy.py comments`, which names the element.

From the tree as well (owner 2026-10-08): hover a row and click its comment button, right-click the row › **Comment**, or select it and press C while the tree has the focus. The board's comment box opens at that element with the anchor a click on it in the page would give, so the pin lands on the element on the card even when it is too small or covered to click. An element that draws no box of its own (`display: contents`) takes its contents' box, and one that isn't drawn takes its nearest ancestor's. One out of sight in a scroller or a slider, even flush with its edge, is scrolled into view, and cancelling the comment scrolls it back. `element.pin` (`kids`, `parent`, `edge`) says when the pin isn't on the element itself. The page itself decides where a pin goes (`agent.js` sight), for live pins and new comments alike: a point on the part of the element you can see. Scroll the element out of its box and its live pin goes away. If the element is below the page's first screen, its pin on the card's picture waits at the bottom edge, and the pin's tooltip and `hy.py comments` say it is further down and give its point in the page. A row with open threads shows how many, a click opens them, and under the pointer a + starts another one. A folded row with threads inside shows a dot. Hovering a row lights its pins on the board, and opening a pin selects its row.

## Install

The plugin runs inside [Hyimg](https://github.com/constantvis/Hyimg). The simplest way is Hyimg's script: it puts this repository beside `hyimg` and links it:

```sh
cd hyimg && ./scripts/install_plugins.sh --dev
```

Or by hand: clone this repository and run `ln -s <path to hyimg-dev-studio> ~/Library/Application\ Support/Hyimg/plugins/dev`, then View › Restart Server in Hyimg. It needs a Hyimg with the studio switch in the dock and `/sandbox/` (October 2026 or later). For the pictures of pages it needs Playwright with Chromium (`python3 -m pip install playwright && python3 -m playwright install chromium`). Without it Quick Look draws the page without its scripts.

**For agents:** don't install the plugin silently. Ask the person whether they want Dev Studio (HTML pages as cards on the board, edited in place like a frame in Figma), and install only after a yes.

## Tests

```sh
HYIMG_REPO=<hyimg checkout> python3 -m pytest tests/test_dev_studio.py tests/test_dev_edit.py tests/test_dev_editmode.py tests/test_live_sharp.py tests/test_mode_lift.py
python3 -m pytest tests/unit && node --test tests/unit/js/
```

**For agents changing the code:** a source file stays around 1000 lines (the check fails above 1100) and a line around 160 characters (fails above 200). A file near the limit is split by responsibility, one concern per module. The rule and its exceptions are in Hyimg's `AGENTS.md`, section «Размер файлов». `scripts/check.sh --fast` in `hyimg` checks this repository too.

## License

[PolyForm Noncommercial 1.0.0](LICENSE): free to use, study and change for yourself and for noncommercial purposes. Commercial use only with the author's permission.
