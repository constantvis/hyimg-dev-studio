"""Dev mode's edits of an HTML file (owner 2026-10-07: «Чтобы я как в Figma мог работать с нашими HTML-файлами»), on its text: no tree is
built and nothing else of the file is touched, so an edit is a few bytes in place and the rest stays byte for byte.

The page in the board's frame is the browser's tree of the file after its scripts ran. To find an element of it in the file, the server
sends the page its own source with every start tag marked by its place, ` data-hy-at="<offset>"` (annotate()); the page parses that copy
with the browser's own parser (DOMParser: the same tree, tbody and implied tags included, no scripts run) and lines it up with the live
tree (agent.js). An element the copy has no partner for was made by a script; one without the mark was implied by the parser. The edits
then name a start tag by its offset and tag, checked here against the file of that revision (its sha1).

Edits, the only ones there are: a property of an element's style attribute (style), the text of an element without elements inside
(text), the value of a custom property declared in a top-level :root or html rule of a <style> of the file (var). Values are checked:
known properties only, no quotes, angle brackets, braces, semicolons, backslashes or comments."""
import hashlib
import html
import re
from html.parser import HTMLParser

MARK = "data-hy-at"
PROPS = ("color", "background-color", "border-color", "border-width", "border-style", "border-radius", "font-size", "font-weight",
         "opacity", "padding", "gap", "width", "height")
RAW = ("title", "textarea", "xmp", "iframe", "noembed", "noframes", "plaintext")   # their content is text to the browser, not tags
IMPLIED_END = ("p", "li", "dt", "dd", "option", "optgroup", "td", "th", "tr", "rb", "rt", "rp")   # their end tag may be left out
VALUE = re.compile(r"[^;{}<>\"'\\\n\r]{1,200}")


class Refused(ValueError):
    """an edit that can't be written, with the reason for the person"""


def decode(data):
    return data.decode("utf-8", "surrogateescape")   # any byte that is not UTF-8 comes back as it was


def encode(text):
    return text.encode("utf-8", "surrogateescape")


def rev(data):
    return hashlib.sha1(data).hexdigest()


class _Scan(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text, self.tags, self.styles, self._open = text, [], [], None
        self.lines = [0] + [m.end() for m in re.finditer("\n", text)]

    def _pos(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        at, raw = self._pos(), self.get_starttag_text() or ""
        if self.text.startswith(raw, at): self.tags.append((at, at + len(raw), tag))
        if tag == "style": self._open = at + len(raw)
        if tag in RAW: self.set_cdata_mode(tag)

    def handle_startendtag(self, tag, attrs):
        at, raw = self._pos(), self.get_starttag_text() or ""
        if self.text.startswith(raw, at): self.tags.append((at, at + len(raw), tag))

    def handle_endtag(self, tag):
        if tag == "style" and self._open is not None:
            self.styles.append((self._open, self._pos())); self._open = None


def scan(text):
    """{"tags": [(start, end, tag)], "styles": [(content start, content end)]} of the file's start tags and <style> blocks"""
    s = _Scan(text)
    try: s.feed(text); s.close()
    except Exception: pass   # the parser gave up on broken markup: what it found stays
    return {"tags": s.tags, "styles": s.styles}


def annotate(text, sc=None):
    """the source with ` data-hy-at="<offset>"` before the closing > of each start tag (a copy for the page's parser, never written)"""
    sc = sc or scan(text)
    out, last = [], 0
    for start, end, _tag in sc["tags"]:
        cut = end - 1   # the start tag's final >
        out.append(text[last:cut]); out.append(f' {MARK}="{start}"'); last = cut
    out.append(text[last:])
    return "".join(out)


def tag_at(text, at):
    """(tag, end of the start tag, attributes) of the start tag at an offset; attributes: [{name, start, end, vstart, vend, q}]"""
    if not isinstance(at, int) or at < 0 or at >= len(text) or text[at] != "<":
        raise Refused("not a start tag in the file")
    m = re.compile(r"<([A-Za-z][^\s/>]*)").match(text, at)
    if not m: raise Refused("not a start tag in the file")
    i, n, attrs = m.end(), len(text), []
    while i < n:
        while i < n and (text[i].isspace() or text[i] == "/"):
            if text[i] == "/" and text.startswith("/>", i): break
            i += 1
        if i >= n: break
        if text[i] == ">": return m.group(1).lower(), i + 1, attrs
        if text.startswith("/>", i): return m.group(1).lower(), i + 2, attrs
        a = re.compile(r"[^\s/>=][^\s/>=]*").match(text, i)
        if not a: i += 1; continue
        item = {"name": a.group(0).lower(), "start": i, "end": a.end(), "vstart": None, "vend": None, "q": ""}
        j = a.end()
        while j < n and text[j].isspace(): j += 1
        if j < n and text[j] == "=":
            j += 1
            while j < n and text[j].isspace(): j += 1
            if j < n and text[j] in "\"'":
                q = text[j]; k = text.find(q, j + 1)
                if k < 0: raise Refused("an attribute's quote is never closed")
                item.update(vstart=j + 1, vend=k, q=q, end=k + 1); j = k + 1
            else:
                v = re.compile(r"[^\s>]*").match(text, j)
                item.update(vstart=j, vend=v.end(), end=v.end()); j = v.end()
        attrs.append(item); i = j
    raise Refused("the start tag never ends")


def _check(prop, value):
    if prop not in PROPS: raise Refused(f"not an editable property: {prop}")
    if value == "": return
    if not isinstance(value, str) or not VALUE.fullmatch(value) or "/*" in value or value.count("(") != value.count(")"):
        raise Refused(f"not a value Dev Studio writes: {str(value)[:60]}")


def _decls(css):
    """[(prop lowercase, start of the declaration, end before its ;, start of its value)] of a declaration list"""
    out, i, n, depth, start, q = [], 0, len(css), 0, 0, ""
    while i <= n:
        c = css[i] if i < n else ";"
        if q:
            if c == q: q = ""
        elif c in "\"'": q = c
        elif c == "(": depth += 1
        elif c == ")": depth = max(0, depth - 1)
        elif c == ";" and depth == 0:
            seg = css[start:i]; m = re.match(r"\s*([-\w]+)\s*:\s*", seg)
            if m: out.append((m.group(1).lower(), start + len(seg) - len(seg.lstrip()), start + len(seg.rstrip()), start + m.end()))
            start = i + 1
        i += 1
    return out


def set_style(text, at, tag, changes):
    """a splice (start, end, new text) that sets each {prop: value} in the element's style attribute ("" removes it)"""
    name, end, attrs = tag_at(text, at)
    if name != tag: raise Refused(f"the file has <{name}> there, not <{tag}>")
    for p, v in changes.items(): _check(p, v)
    st = [a for a in attrs if a["name"] == "style"]
    if not st:
        add = "; ".join(f"{p}: {v}" for p, v in changes.items() if v)
        if not add: return None
        cut = end - 2 if text.startswith("/>", end - 2) and (not attrs or text[end - 3] in " \"'") else end - 1
        return cut, cut, f' style="{add}"'
    a = st[-1]
    if a["vstart"] is None: old, q = "", '"'
    else: old, q = text[a["vstart"]:a["vend"]], a["q"] or '"'
    if any(q in (v or "") for v in changes.values()): raise Refused("the value has the attribute's quote")
    css = old
    for p, v in changes.items():
        found = [d for d in _decls(css) if d[0] == p]
        if found:
            _p, ds, de, vs = found[-1]
            if v: css = css[:vs] + v + css[de:]
            elif not css[de:].strip(" \t\r\n;"):   # the last one: the separator before it goes, the list's own ending stays
                rest = css[de:]; head = css[:ds].rstrip().rstrip(";").rstrip()
                css = head + (";" if head and rest.strip() == ";" else "") + rest[len(rest.rstrip()):]
            else:
                tail = re.match(r"\s*;?\s*", css[de:]).end()
                css = css[:ds] + css[de + tail:]
        elif v:
            body = css.rstrip(); ws = css[len(body):]
            semi = body.endswith(";")
            css = body + ("" if not body else " " if semi else "; ") + f"{p}: {v}" + (";" if semi else "") + ws
    if not css.strip():   # nothing left: the attribute goes with the space before it
        s = a["start"]
        while s > at and text[s - 1].isspace(): s -= 1
        return s, a["end"], ""
    if a["vstart"] is None or not a["q"]:
        return a["start"], a["end"], f'style="{css}"'
    return a["vstart"], a["vend"], css


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def set_text(text, at, tag, was, new):
    """a splice that replaces the text of an element with no elements inside; `was`, the text the page parsed from the file, must match"""
    name, end, _a = tag_at(text, at)
    if name != tag: raise Refused(f"the file has <{name}> there, not <{tag}>")
    if not isinstance(new, str) or len(new) > 20000: raise Refused("the text is too long")
    nxt = text.find("<", end)
    if nxt < 0: nxt = len(text)
    closes = re.match(r"</" + re.escape(name) + r"[\s>]", text[nxt:nxt + len(name) + 3], re.I)
    if not closes and not (name in IMPLIED_END and re.match(r"</?[A-Za-z]", text[nxt:nxt + 2])):
        raise Refused("the element has a comment or markup inside its text")
    content = text[end:nxt]
    if norm(html.unescape(content)) != norm(was): raise Refused("the text in the file is not the text the page shows: a script changed it")
    lead, body = content[:len(content) - len(content.lstrip())], content.strip()
    trail = content[len(lead) + len(body):]
    esc = new.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return end + len(lead), end + len(lead) + len(body), esc


def _rules(css):
    """[(selector, inside an at-rule, body start, body end)] of a stylesheet, comments and strings skipped"""
    clean = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)
    out, stack, start, i, q = [], [], 0, 0, ""
    while i < len(clean):
        c = clean[i]
        if q:
            if c == q: q = ""
        elif c in "\"'": q = c
        elif c == "{":
            pre = clean[start:i].strip(); stack.append((pre, i + 1)); start = i + 1
        elif c == "}":
            if stack:
                pre, b = stack.pop()
                if not pre.startswith("@"): out.append((pre, any(p.startswith("@") for p, _ in stack), b, i))
            start = i + 1
        elif c == ";": start = i + 1
        i += 1
    return out


ROOTSEL = re.compile(r"^(:root|html)$", re.I)


def vars_of(text, sc=None):
    """the custom properties declared in the file's <style> blocks: [{name, value, where: "root" | "media" | "other", uses}]; root is a
    top-level :root or html rule (the one an «everywhere» edit writes), uses counts var(--name) in the whole file"""
    sc = sc or scan(text)
    found = {}
    for cs, ce in sc["styles"]:
        css = text[cs:ce]
        for sel, nested, b, e in _rules(css):
            for p, ds, de, vs in _decls(css[b:e]):
                if not p.startswith("--"): continue
                root = not nested and any(ROOTSEL.match(s.strip()) for s in sel.split(","))
                where = "root" if root else "media" if nested else "other"
                cur = found.get(p)
                if not cur or (where == "root" and cur["where"] != "root"):
                    found[p] = {"name": p, "value": css[b + vs:b + de].strip(), "where": where}
    for v in found.values():
        v["uses"] = len(re.findall(r"var\(\s*" + re.escape(v["name"]) + r"\s*[,)]", text))
    return sorted(found.values(), key=lambda v: v["name"])


def set_var(text, name, value, sc=None):
    """a splice that sets the custom property's value in the first top-level :root or html rule that declares it"""
    if not re.fullmatch(r"--[\w-]{1,80}", name or ""): raise Refused("not a custom property")
    if not isinstance(value, str) or not value.strip() or not VALUE.fullmatch(value) or "/*" in value or value.count("(") != value.count(")"):
        raise Refused(f"not a value Dev Studio writes: {str(value)[:60]}")
    sc = sc or scan(text)
    for cs, ce in sc["styles"]:
        css = text[cs:ce]
        for sel, nested, b, e in _rules(css):
            if nested or not any(ROOTSEL.match(s.strip()) for s in sel.split(",")): continue
            for p, ds, de, vs in _decls(css[b:e]):
                if p == name.lower():
                    old = css[b + vs:b + de]; lead = len(old) - len(old.lstrip())
                    return cs + b + vs + lead, cs + b + de, value.strip()
    raise Refused(f"{name} is not declared in a :root rule of this file")


def apply(text, ops):
    """the file's text with the ops: [{op: "style", at, tag, set: {prop: value}} | {op: "text", at, tag, was, text} | {op: "var", name, value}]"""
    if not isinstance(ops, list) or not ops or len(ops) > 200: raise Refused("no edits")
    sc, merged, cuts = None, {}, []
    for o in ops:
        if not isinstance(o, dict): raise Refused("not an edit")
        if o.get("op") == "style":
            if not isinstance(o.get("set"), dict) or not o["set"]: raise Refused("no properties")
            k = (o.get("at"), o.get("tag"))
            merged.setdefault(k, {}).update({str(p): ("" if v is None else str(v).strip()) for p, v in o["set"].items()})
        elif o.get("op") == "text":
            cuts.append(set_text(text, o.get("at"), o.get("tag"), o.get("was"), o.get("text")))
        elif o.get("op") == "var":
            sc = sc or scan(text)
            cuts.append(set_var(text, o.get("name"), o.get("value"), sc))
        else:
            raise Refused(f"not an edit Dev Studio makes: {str(o.get('op'))[:40]}")
    for (at, tag), ch in merged.items():
        cuts.append(set_style(text, at, tag, ch))
    cuts = sorted((c for c in cuts if c), key=lambda c: (c[0], c[1]))
    for a, b in zip(cuts, cuts[1:]):
        if b[0] < a[1]: raise Refused("two edits touch the same place")
    for s, e, new in reversed(cuts):
        text = text[:s] + new + text[e:]
    return text
