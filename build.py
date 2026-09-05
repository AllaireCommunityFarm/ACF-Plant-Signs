#!/usr/bin/env python3
"""
Allaire Community Farm - plant sign page builder.

Reads plants.json and writes:
  site/p/NN/index.html   one page per sign number
  site/index.html        directory of all signs
  qr/acf-pNN.png         QR code for each sign number

Sign numbers are permanent. Plants are assigned to sign numbers in
plants.json and can be reassigned any time without recutting a plate.
"""

import json, os, shutil
import qrcode
from qrcode.constants import ERROR_CORRECT_H

BASE = "https://allairecommunityfarm.github.io/ACF-Plant-Signs"
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
QR = os.path.join(ROOT, "qr")

CSS = """
:root{--ink:#2f2a24;--green:#3d5c3a;--red:#9c3b2e;--paper:#faf6ee;--rule:#d8cdb8}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:17px/1.6 Georgia,'Iowan Old Style',serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:640px;margin:0 auto;padding:28px 22px 64px}
header{text-align:center;border-bottom:2px solid var(--rule);padding-bottom:18px;margin-bottom:26px}
.mark{font:600 13px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.16em;
  text-transform:uppercase;color:var(--green)}
.tag{font-style:italic;color:#6d6455;font-size:14px;margin-top:6px}
h1{font-size:31px;line-height:1.15;margin:0 0 4px}
.sci{font-style:italic;color:#6d6455;margin:0 0 2px}
.fam{font:600 12px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.12em;
  text-transform:uppercase;color:var(--red);margin:10px 0 0}
.facts{list-style:none;padding:0;margin:24px 0;border-top:1px solid var(--rule)}
.facts li{display:flex;gap:14px;padding:11px 2px;border-bottom:1px solid var(--rule)}
.facts b{flex:0 0 34%;font:600 12px/1.5 -apple-system,Segoe UI,sans-serif;
  letter-spacing:.09em;text-transform:uppercase;color:var(--green)}
.facts span{flex:1}
h2{font:600 12px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.13em;
  text-transform:uppercase;color:var(--green);margin:30px 0 10px}
footer{margin-top:44px;padding-top:18px;border-top:2px solid var(--rule);
  text-align:center;font-size:14px;color:#6d6455}
footer a{color:var(--green)}
.num{font:600 12px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.12em;
  color:#a89c86;text-transform:uppercase}
.soon{background:#fff;border:1px solid var(--rule);border-radius:4px;
  padding:26px 22px;text-align:center;margin:30px 0}
.soon p{margin:0 0 6px;font-size:16px}
.soon .small{font-size:14px;color:#6d6455;margin:0}
.list{list-style:none;padding:0;margin:0}
.list li{border-bottom:1px solid var(--rule)}
.list a{display:flex;gap:12px;padding:14px 2px;text-decoration:none;color:var(--ink)}
.list .n{flex:0 0 34px;font:600 13px/1.6 -apple-system,Segoe UI,sans-serif;color:#a89c86}
.list .pending{color:#a89c86;font-style:italic}
"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{root}/style.css">
</head>
<body>
<div class="wrap">
<header>
  <div class="mark">Allaire Community Farm</div>
  <div class="tag">We Nurture Through Nature</div>
</header>
"""

FOOT = """<footer>
  <p>Allaire Community Farm &middot; Wall Township, New Jersey<br>
  <a href="{root}/">All plant signs</a></p>
  <p class="num">Sign {num}</p>
</footer>
</div>
</body>
</html>
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


FARM = "https://allairecommunityfarm.org/"

REDIRECT = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url={target}" />
</head>
<body></body>
</html>
"""


def page(entry, num, root):
    common = entry.get("common_name", "")
    if entry.get("redirect"):
        return REDIRECT.format(target=esc(entry["redirect"]))
    if not common:
        title = f"Sign {num} - Allaire Community Farm"
        desc = "Plant sign at Allaire Community Farm."
        body = (f'<h1>Sign {num}</h1>'
                '<div class="soon"><p>This plant\u2019s page is being written.</p>'
                '<p class="small">Check back soon, or ask a staff member or '
                'volunteer about this plant.</p></div>'
                f'<p style="text-align:center"><a href="{FARM}">'
                'allairecommunityfarm.org</a></p>')
    else:
        title = f"{common} - Allaire Community Farm"
        desc = (entry.get("description", "") or common)[:150]
        body = f'<h1>{esc(common)}</h1>'
        if entry.get("scientific_name"):
            body += f'<p class="sci">{esc(entry["scientific_name"])}</p>'
        if entry.get("family"):
            body += f'<p class="fam">{esc(entry["family"])}</p>'
        if entry.get("description"):
            body += f'<h2>About</h2><p>{esc(entry["description"])}</p>'

        rows = [("Type", "plant_type"), ("Light", "light"), ("Water", "water"),
                ("Hardiness", "zone"), ("Bloom", "bloom"),
                ("Edible parts", "edible"), ("Uses", "uses"),
                ("Native to", "origin")]
        facts = "".join(
            f"<li><b>{lbl}</b><span>{esc(entry[k])}</span></li>"
            for lbl, k in rows if entry.get(k))
        if facts:
            body += f'<h2>At a glance</h2><ul class="facts">{facts}</ul>'

        if entry.get("pet_toxicity"):
            body += (f'<h2>Pets</h2><p>{esc(entry["pet_toxicity"])}</p>')
        if entry.get("notes"):
            body += f'<h2>Notes</h2><p>{esc(entry["notes"])}</p>'

    return (HEAD.format(title=esc(title), desc=esc(desc), root=root)
            + body + FOOT.format(root=root, num=num))


def index_page(plants):
    rows = ""
    for num in sorted(plants):
        e = plants[num]
        name = e.get("common_name", "") or e.get("redirect_label", "")
        label = (f'<span>{esc(name)}</span>' if name
                 else '<span class="pending">Awaiting content</span>')
        rows += (f'<li><a href="p/{num}/"><span class="n">{num}</span>'
                 f'{label}</a></li>')
    return (HEAD.format(title="Plant Signs - Allaire Community Farm",
                        desc="Directory of plant signs at Allaire Community Farm.",
                        root=".")
            + f'<h1>Plant Signs</h1><p class="sci">Scan a sign in the garden, '
              f'or browse the list below.</p><ul class="list">{rows}</ul>'
            + """<footer>
  <p>Allaire Community Farm &middot; Wall Township, New Jersey</p>
</footer>
</div>
</body>
</html>
""")


def make_qr(url, path):
    q = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                      box_size=40, border=4)
    q.add_data(url)
    q.make(fit=True)
    img = q.make_image(fill_color="black", back_color="white")
    img.save(path)
    return q.version, img.size[0]


def main():
    with open(os.path.join(ROOT, "plants.json")) as f:
        plants = json.load(f)

    shutil.rmtree(SITE, ignore_errors=True)
    shutil.rmtree(QR, ignore_errors=True)
    os.makedirs(os.path.join(SITE, "p"))
    os.makedirs(QR)

    with open(os.path.join(SITE, "style.css"), "w") as f:
        f.write(CSS)
    with open(os.path.join(SITE, ".nojekyll"), "w") as f:
        f.write("")

    for num in sorted(plants):
        d = os.path.join(SITE, "p", num)
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(page(plants[num], num, "../.."))
        url = f"{BASE}/p/{num}/"
        v, px = make_qr(url, os.path.join(QR, f"acf-p{num}.png"))
        if num == "01":
            print(f"QR: {url}  version {v}  {px}x{px}px")

    with open(os.path.join(SITE, "index.html"), "w") as f:
        f.write(index_page(plants))

    print(f"Built {len(plants)} pages.")


if __name__ == "__main__":
    main()
