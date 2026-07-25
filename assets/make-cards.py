#!/usr/bin/env python3
"""Regenerate the app cards used by the profile README.

Each card is a rendered image because GitHub strips CSS from README HTML —
inline `style` attributes are removed by its sanitizer, so a real coloured
card is only possible as a picture.

Every card's gradient comes from that app's own icon, darkened until white
body text clears WCAG AA (4.5:1). The script prints the measured contrast
for each card and marks anything that falls short.

    python3 assets/make-cards.py

Requires: Google Chrome (headless rendering) and Pillow (WebP encode).
"""
import base64
import colorsys
import os
import subprocess
import tempfile

OUT = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="cards-")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def lum(rgb):
    def ch(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_white(rgb):
    return 1.05 / (lum(rgb) + 0.05)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def darken_until(hexcolor, target=4.8):
    """Scale a colour's HSV value down until white text clears `target`."""
    r, g, b = hexrgb(hexcolor)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    rgb = (r, g, b)
    for _ in range(120):
        rgb = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
        if contrast_white(rgb) >= target:
            break
        v *= 0.98
    return "#%02X%02X%02X" % rgb, contrast_white(rgb)


CARDS = [
    dict(key="journeybot", icon="journeybot.png", name="journeybot",
         tagline="Pack smart. Enjoy the journey.",
         body="A trip planner that builds a packing list for your real destination, "
              "dates, and plans — generated on-device with Apple Intelligence.",
         platform="iPhone · iPad · Mac", light="#E05A33", deep="#7A2712"),
    dict(key="timo", icon="timo.png", name="Timo",
         tagline="Your world, at a glance.",
         body="World clocks side by side with the time difference already worked out. "
              "Each card shifts colour through dawn, day, dusk, and night.",
         platform="iPhone", light="#3D8FDB", deep="#123A6B"),
    dict(key="hotspot-meter", icon="hotspot-meter.png", name="Hotspot Meter",
         tagline="Track every megabyte your Mac uses.",
         body="A menu bar app that counts your data in real time on every network — "
              "live speeds, per-network history, and alerts before your cap.",
         platform="Mac", light="#0B78D8", deep="#06183F"),
    dict(key="kahudo", icon="kahudo.png", name="Kahudo",
         tagline="Think ahead, place smart.",
         body="A cosmic tile strategy puzzle. Build poker hands or dice combinations "
              "on a grid. Quick rounds, or long score-chasing runs.",
         platform="iPhone", light="#9B31A0", deep="#2B1552"),
]

TPL = """<!doctype html><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ background:transparent; }}
  body {{ width:640px; height:342px;
    font-family:-apple-system,"SF Pro Display","SF Pro Text",system-ui,sans-serif;
    -webkit-font-smoothing:antialiased; }}
  .card {{ width:640px; height:342px; border-radius:26px; overflow:hidden;
    padding:44px 46px 40px; display:flex; flex-direction:column;
    background:
      radial-gradient(620px 380px at 88% -18%, rgba(255,255,255,.20), transparent 62%),
      linear-gradient(148deg, {light} 0%, {deep} 100%);
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.13); }}
  .top {{ display:flex; align-items:center; gap:20px; }}
  .icon {{ width:78px; height:78px; border-radius:18px; flex:none;
    box-shadow:0 8px 22px rgba(0,0,0,.34); }}
  h1 {{ font-size:35px; font-weight:700; letter-spacing:-.022em; color:#fff; line-height:1.1; }}
  .tagline {{ margin-top:26px; font-size:20px; font-weight:600; letter-spacing:-.012em;
    color:rgba(255,255,255,.96); }}
  .body {{ margin-top:12px; font-size:17.5px; line-height:1.52; color:rgba(255,255,255,.88);
    letter-spacing:-.004em; }}
  .spacer {{ flex:1; min-height:16px; }}
  .platform {{ align-self:flex-start; font-size:13.5px; font-weight:640; letter-spacing:.07em;
    text-transform:uppercase; color:#fff; padding:9px 16px; border-radius:999px;
    background:rgba(255,255,255,.19);
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.26); }}
</style>
<div class="card">
  <div class="top">
    <img class="icon" src="data:image/png;base64,{icon}" />
    <h1>{name}</h1>
  </div>
  <div class="tagline">{tagline}</div>
  <div class="body">{body}</div>
  <div class="spacer"></div>
  <div class="platform">{platform}</div>
</div>"""


def main():
    from PIL import Image

    print("%-15s %-19s %-22s status" % ("app", "gradient", "white-text contrast"))
    for c in CARDS:
        light, ratio = darken_until(c["light"])
        deep_ratio = contrast_white(hexrgb(c["deep"]))
        ok = ratio >= 4.5 and deep_ratio >= 4.5
        print("%-15s %s->%s  %5.2f:1 / deep %5.2f:1   %s"
              % (c["key"], c["light"], light, ratio, deep_ratio, "OK" if ok else "FAIL"))

        icon = base64.b64encode(open(os.path.join(OUT, c["icon"]), "rb").read()).decode()
        html_path = os.path.join(TMP, c["key"] + ".html")
        with open(html_path, "w") as fh:
            fh.write(TPL.format(light=light, deep=c["deep"], icon=icon, name=c["name"],
                                tagline=c["tagline"], body=c["body"],
                                platform=c["platform"]))

        png = os.path.join(TMP, c["key"] + ".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2",
                        "--default-background-color=00000000",
                        "--window-size=640,342", "--screenshot=" + png,
                        "file://" + html_path], check=True, capture_output=True)

        # Chrome only writes PNG; WebP keeps the profile page ~10x lighter.
        webp = os.path.join(OUT, "card-" + c["key"] + ".webp")
        Image.open(png).save(webp, "WEBP", quality=90, method=6)

    print("\nwrote %s to %s" % (", ".join("card-%s.webp" % c["key"] for c in CARDS), OUT))


if __name__ == "__main__":
    main()
