#!/usr/bin/env python3
"""
Build سایت گهرتایر خرم‌آباد

این اسکریپت هدر/فوتر مشترک و لیست محصولات را می‌سازد.

برای افزودن/ویرایش محصولات:
  1) فایل products.json را ویرایش کنید.
  2) در همین پوشه اجرا کنید: python3 build.py

کارت‌های داخل products.html خروجی build هستند و بهتر است مستقیماً ویرایش نشوند.
"""
import datetime
import glob
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def pages_in(pattern):
    """glob با جداکنندهٔ همیشه «/» (روی ویندوز هم) تا کلید صفحه‌ها در همه‌جا یکسان باشد."""
    return sorted(p.replace(os.sep, "/") for p in glob.glob(pattern))


def active_for(name):
    if name == "index.html": return "home"
    if name == "about.html": return "about"
    if name == "contact.html": return "contact"
    if name == "wholesale.html": return "wholesale"
    if name == "products.html" or name.startswith(("products/", "categories/")): return "products"
    if name == "articles.html" or name.startswith("articles/"): return "articles"
    return None


def esc(value):
    return html.escape(str(value or ""), quote=True)


def clean_search(*parts):
    return " ".join(str(x or "") for x in parts if str(x or "").strip()).strip().lower()


def product_title(p):
    vehicle = p.get("vehicle", "").strip()
    size = p.get("size", "").strip()
    brand = p.get("brand", "").strip()
    if vehicle:
        return f"لاستیک {size} {vehicle} | {brand}" if size else f"لاستیک {vehicle} | {brand}"
    return f"لاستیک {size} | {brand}" if brand else f"لاستیک {size}"


def render_product_card(p):
    """کارت محصول بدون تورفتگی و خط خالی اضافه (فاصلهٔ سفید در HTML همان یک فاصله حساب می‌شود)."""
    html = _render_product_card_raw(p)
    html = re.sub(r"\n[ \t]+", "\n", html)
    return re.sub(r"\n{2,}", "\n", html)


def _render_product_card_raw(p):
    title = product_title(p)
    vehicle = p.get("vehicle", "").strip()
    size = p.get("size", "").strip()
    brand = p.get("brand", "").strip()
    category = int(p.get("category", 5))
    image = p.get("image") or "assets/images/pride-165-65r13-gahar-tire.jpg"
    link = p.get("link")
    available = bool(p.get("available", True))
    description = p.get("description", "")
    # فقط چیزهایی که کاربر واقعاً جستجو می‌کند (نه کل کپشن؛ آن کپشن در خود صفحهٔ محصول هست)
    search = clean_search(title, vehicle, size, size.replace("/", " ").replace("-", " "), brand)
    m_size = re.fullmatch(r"(\d{3})/(\d{2})R(\d{2})", size.upper().replace(" ", ""))
    size_attrs = (f' data-width="{m_size.group(1)}" data-profile="{m_size.group(2)}" data-rim="{m_size.group(3)}"'
                  if m_size else "")

    if link:
        action = f'''<a href="{esc(link)}" class="btn btn-digi rounded-pill px-3 py-2 fw-bold d-flex align-items-center gap-2 shadow-sm transition-all">
                                <span>مشاهده</span>
                                <i class="fa-solid fa-arrow-left"></i>
                            </a>'''
    else:
        action = '''<a href="tel:09120346053" class="btn btn-digi rounded-pill px-3 py-2 fw-bold d-flex align-items-center gap-2 shadow-sm transition-all">
                                <span>استعلام</span>
                                <i class="fa-solid fa-phone"></i>
                            </a>'''

    meta=[]
    if vehicle: meta.append(f'<span class="badge rounded-pill bg-light text-secondary border">{esc(vehicle)}</span>')
    if size: meta.append(f'<span class="badge rounded-pill bg-light text-secondary border" dir="ltr">{esc(size)}</span>')
    if brand: meta.append(f'<span class="badge rounded-pill bg-light text-secondary border">{esc(brand)}</span>')
    meta_html='\n                                '.join(meta)
    main_t, _, brand_t = title.partition(" | ")
    title_html = f'{esc(main_t)}<span class="pc-t-brand"> | {esc(brand_t)}</span>' if brand_t else esc(title)
    sub_parts=[x for x in (brand,) if x]
    sub_html=f'<div class="pc-sub d-md-none"><i class="fa-solid fa-tag"></i><span>{esc(" · ".join(sub_parts))}</span></div>' if sub_parts else ''

    stock_html = '''<span class="badge pc-stock pc-stock-ok bg-success-subtle text-success border border-success-subtle position-absolute top-0 start-0 m-3 px-3 py-1.5 rounded-pill fs-7 fw-bold">
                            <i class="fa-solid fa-check ms-1"></i> موجود
                        </span>''' if available else '''<span class="badge pc-stock pc-stock-ask bg-secondary-subtle text-secondary border border-secondary-subtle position-absolute top-0 start-0 m-3 px-3 py-1.5 rounded-pill fs-7 fw-bold">
                            <i class="fa-solid fa-clock ms-1"></i> استعلام موجودی
                        </span>'''

    # Existing products keep their detail links; new catalog-only products go to phone inquiry.
    title_link_start = f'<a href="{esc(link)}" class="text-decoration-none">' if link else '<span class="text-decoration-none">'
    title_link_end = '</a>' if link else '</span>'

    return f'''        <div class="col product-col" data-cat="{category}" data-search="{esc(search)}"{size_attrs}>
            <div class="card h-100 border-0 shadow-sm rounded-4 card-product bg-white overflow-hidden d-flex flex-column position-relative">

                <div class="position-relative p-4 text-center product-img-wrapper d-flex align-items-center justify-content-center">
                    <img src="{esc(image)}" alt="{esc(title)}" class="img-fluid product-card-img rounded-3" loading="lazy">
                    {stock_html}
                </div>

                <div class="card-body d-flex flex-column p-4">
                    {title_link_start}
                        <h5 class="card-title fw-bold text-dark lh-base mb-3 text-truncate-2" title="{esc(title)}">{title_html}</h5>
                    {title_link_end}

                    {sub_html}
                    <div class="d-none d-md-flex flex-wrap gap-2 mb-3 product-meta">
                        {meta_html}
                    </div>

                    <div class="mt-auto pt-3 border-top d-flex align-items-center justify-content-between gap-2">
                        <div>
                            <small class="text-muted d-block fs-7 mb-1">قیمت:</small>
                            <span class="fw-extrabold text-digi fs-6">استعلام با تماس</span>
                        </div>
                        {action}
                    </div>
                </div>
            </div>
        </div>'''


# ---------------------------------------------------------------------------
# بهینه‌سازی: تصاویر (WebP + width/height)، CSS (ادغام + minify)، head مشترک
# ---------------------------------------------------------------------------
THEME_COLOR = "#ef4056"
BASE_CSS = ("assets/css/bootstrap.rtl.purged.css", "assets/fa/fa-subset.css", "assets/css/icons-extra.css", "assets/css/fonts.css")
PRELOADS = (("assets/fonts/Vazirmatn-VF.woff2", "font/woff2"), ("assets/fa/webfonts/subset-solid.woff2", "font/woff2"))
MAX_IMG = 900  # بیشترین ضلع تصویر خروجی (پیکسل)

IMG_DIMS = {}


def optimize_images():
    """برای هر JPG/PNG در assets/images یک WebP کنار آن می‌سازد (فقط اگر نبود یا قدیمی‌تر بود)
    و ابعاد را برای width/height ثبت می‌کند. نیازمند Pillow؛ اگر نصب نباشد، همان JPG استفاده می‌شود."""
    try:
        from PIL import Image
    except ImportError:
        print("!! Pillow نصب نیست؛ تصاویر WebP ساخته نشدند. برای فعال‌سازی: pip install pillow")
        return
    made = 0
    for src in sorted(glob.glob("assets/images/*.jpg") + glob.glob("assets/images/*.jpeg") + glob.glob("assets/images/*.png")):
        out = os.path.splitext(src)[0] + ".webp"
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
            im = Image.open(src)
            im.load()
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            if max(im.size) > MAX_IMG:
                im.thumbnail((MAX_IMG, MAX_IMG), Image.LANCZOS)
            im.save(out, "WEBP", quality=80, method=6)
            made += 1
        with Image.open(out) as im:
            IMG_DIMS[out.replace(os.sep, "/")] = im.size
    for out in glob.glob("assets/images/*.webp"):
        if out.replace(os.sep, "/") not in IMG_DIMS:
            with Image.open(out) as im:
                IMG_DIMS[out.replace(os.sep, "/")] = im.size
    print(f"images: {len(IMG_DIMS)} webp ({made} new)")


def process_images(s):
    """<img>: مسیر JPG را به WebP تغییر می‌دهد و width/height/lazy/decoding را اضافه می‌کند."""
    def fix(m):
        tag = m.group(0)
        sm = re.search(r'\bsrc="(assets/images/[^"]+?)\.(?:jpe?g|png)"', tag)
        if not sm:
            return tag
        webp = sm.group(1) + ".webp"
        if webp not in IMG_DIMS:
            return tag
        w, h = IMG_DIMS[webp]
        tag = tag.replace(sm.group(0), f'src="{webp}"')
        if not re.search(r"\bwidth=", tag):
            tag = tag[:-1].rstrip() + f' width="{w}" height="{h}">'
        if not re.search(r"\bdecoding=", tag):
            tag = tag[:-1].rstrip() + ' decoding="async">'
        if not re.search(r"\bloading=", tag):
            if "style-main-img" in tag:      # تصویر اصلی صفحهٔ محصول = LCP
                tag = tag[:-1].rstrip() + ' fetchpriority="high">'
            else:
                tag = tag[:-1].rstrip() + ' loading="lazy">'
        return tag
    return re.sub(r"<img\b[^>]*>", fix, s)


def process_icons_a11y(s):
    """آیکون‌های تزئینی از صفحه‌خوان پنهان می‌شوند."""
    return re.sub(r'<i class="(fa-(?:solid|brands)[^"]*)"(?![^>]*aria-hidden)>',
                  r'<i class="\1" aria-hidden="true">', s)


def minify_css(css, src_path, dst_dir):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    def rel(m):
        u = m.group(2).strip()
        if u.startswith(("data:", "http", "//", "/", "#")):
            return m.group(0)
        new = os.path.relpath(os.path.join(os.path.dirname(src_path), u), dst_dir).replace(os.sep, "/")
        return f"url({m.group(1)}{new}{m.group(1)})"
    css = re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", rel, css)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>~])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


CSS_BUNDLES = {}   # key -> href


def build_css_bundle(name, files):
    dst_dir = "assets/dist"
    os.makedirs(dst_dir, exist_ok=True)
    body = "\n".join(minify_css(read(f), f, dst_dir) for f in files)
    ver = hashlib.md5(body.encode("utf-8")).hexdigest()[:8]
    out = f"{dst_dir}/{name}.min.css"
    write(out, body)
    CSS_BUNDLES[name] = f"{out}?v={ver}"
    return CSS_BUNDLES[name]


def head_block(custom):
    base = build_css_bundle("base", BASE_CSS)
    key = "page-" + "-".join(custom) if custom else "page-none"
    page = build_css_bundle(key, [f"assets/css/{c}.css" for c in custom]) if custom else None
    lines = [f'<!-- @@css:start custom={",".join(custom)} -->',
             f'<meta name="theme-color" content="{THEME_COLOR}">',
             '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">',
             '<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">',
             '<link rel="manifest" href="manifest.json">']
    for path, typ in PRELOADS:
        lines.append(f'<link rel="preload" href="{path}" as="font" type="{typ}" crossorigin>')
    lines.append(f'<link rel="stylesheet" href="{base}">')
    if page:
        lines.append(f'<link rel="stylesheet" href="{page}">')
    lines.append('<!-- @@css:end -->')
    return "\n    ".join(lines)


def process_head(s):
    m = re.search(r"<!-- @@css:start custom=([^ >]*) -->", s)
    if m:
        custom = [c for c in m.group(1).split(",") if c]
        return re.sub(r"<!-- @@css:start .*?<!-- @@css:end -->", lambda _: head_block(custom), s, count=1, flags=re.S)
    # اولین بار: لینک‌های قدیمی stylesheet را پیدا و با بلوک جدید عوض می‌کنیم
    pat = re.compile(r'[ \t]*<link rel="stylesheet" href="assets/(?:css|fa)/([^"]+)">[ \t]*\n?')
    found = list(pat.finditer(s))
    if not found:
        return s
    skip = {"bootstrap.rtl.min.css", "all.min.css", "fonts.css"}
    custom = [os.path.splitext(f.group(1).split("/")[-1])[0] for f in found if f.group(1).split("/")[-1] not in skip]
    first = found[0].start()
    s = pat.sub("", s)
    return s[:first] + "    " + head_block(custom) + "\n" + s[first:]



# ---------------------------------------------------------------------------
# صفحهٔ اختصاصی + کپشن برای همهٔ محصولات (خروجی از products.json)
# ---------------------------------------------------------------------------
CAT_INFO = {
    5: ("لاستیک سواری", "رانندگی شهری و بین‌شهری", "خودروهای سواری"),
    6: ("لاستیک وانت", "حمل بار سبک تا متوسط", "وانت و کامیونت"),
    7: ("لاستیک آفرود", "مسیرهای شهری، جاده‌ای و خاکی", "خودروهای آفرود و دو‌کابین"),
    8: ("لاستیک سنگین", "حمل بار سنگین و مسیرهای طولانی", "کامیون و اتوبوس"),
}
CATEGORY_LANDINGS = {
    5: {"slug": "passenger-tires", "short": "لاستیک‌های سواری", "h1": "لاستیک سواری در خرم‌آباد",
        "title": "لاستیک سواری در خرم‌آباد | سایز و برند | گهرتایر",
        "description": "فهرست لاستیک‌های سواری گهرتایر در خرم‌آباد؛ انواع سایز برای پراید، پژو، سمند، تیبا و دنا از برندهای مختلف. قیمت و موجودی روز با تماس یا واتساپ.",
        "intro": "در این صفحه، لاستیک‌های سواری موجود در کاتالوگ گهرتایر خرم‌آباد را بر اساس سایز، خودرو و برند می‌بینید. محصولات این دسته برای استفاده روزمره و مسیرهای شهری و بین‌شهری ثبت شده‌اند و مشخصات هر مورد در صفحه اختصاصی آن قرار دارد."},
    6: {"slug": "pickup-tires", "short": "لاستیک‌های وانت", "h1": "لاستیک وانت در خرم‌آباد",
        "title": "لاستیک وانت در خرم‌آباد | سایز و موجودی | گهرتایر",
        "description": "فهرست لاستیک وانت و خودروهای باری سبک در گهرتایر خرم‌آباد؛ سایزهای 700R16، 750-16 و 750R16 برای نیسان. استعلام قیمت و موجودی روز با تماس یا واتساپ.",
        "intro": "این صفحه مخصوص لاستیک‌های وانت و خودروهای باری سبک است که در کاتالوگ گهرتایر ثبت شده‌اند. در هر محصول سایز و کاربرد خودرو مشخص شده تا بتوانید قبل از تماس، گزینه‌های موجود را مقایسه و سپس موجودی روز را استعلام کنید."},
    7: {"slug": "offroad-tires", "short": "لاستیک‌های آفرود", "h1": "لاستیک آفرود و دوکابین در خرم‌آباد",
        "title": "لاستیک آفرود در خرم‌آباد | هایلوکس و دوکابین | گهرتایر",
        "description": "فهرست لاستیک‌های آفرود و دوکابین گهرتایر خرم‌آباد؛ سایزهای مختلف برای تویوتا هایلوکس و مسیرهای شهری، جاده‌ای و خاکی. استعلام قیمت و موجودی با تماس.",
        "intro": "در این دسته، لاستیک‌های ثبت‌شده برای خودروهای دوکابین و آفرودی قرار گرفته‌اند. سایز، خودرو و برند هر محصول جداگانه نمایش داده می‌شود تا انتخاب بر اساس مشخصات واقعی خودرو انجام شود و قیمت و موجودی روز از فروشگاه استعلام شود."},
    8: {"slug": "heavy-tires", "short": "لاستیک‌های سنگین", "h1": "لاستیک سنگین و کامیونی در خرم‌آباد",
        "title": "لاستیک سنگین و کامیونی در خرم‌آباد | گهرتایر",
        "description": "فهرست لاستیک سنگین و کامیونی گهرتایر خرم‌آباد؛ سایزهای 900-20، 1000-20، 1200-20 و 1200-24 برای کامیون و اتوبوس. استعلام قیمت و موجودی روز.",
        "intro": "این صفحه مجموعه لاستیک‌های سنگین و کامیونی موجود در کاتالوگ گهرتایر را یکجا نمایش می‌دهد. برای هر محصول سایز و نوع کاربرد ثبت شده است تا بتوانید گزینه مناسب خودرو را پیدا کرده و سپس مشخصات، تاریخ تولید و موجودی واقعی را با فروشگاه بررسی کنید."},
}
CATEGORY_BY_SLUG = {v["slug"]: k for k,v in CATEGORY_LANDINGS.items()}
# نقشهٔ آدرس قدیمی ← آدرس جدید (redirects.json). فقط وقتی اسلاگ یا پوشهٔ صفحه‌ای را عوض می‌کنید اضافه کنید.
REDIRECTS = json.loads(read("redirects.json")) if os.path.exists("redirects.json") else {}
FA_DIGITS = str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")


def fa(n):
    return str(n).translate(FA_DIGITS)


def explain_size(size):
    """توضیح خوانا دربارهٔ معنی سایز؛ اگر الگو ناشناخته باشد None برمی‌گرداند."""
    s = size.strip().upper().replace(" ", "")
    m = re.fullmatch(r"(\d{3})/(\d{2})R(\d{2})", s)
    if m:
        w, r, d = m.groups()
        return (f"در سایز {size}، عدد {fa(w)} عرض لاستیک به میلی‌متر، عدد {fa(r)} نسبت ارتفاع دیواره به عرض (به درصد) "
                f"و {fa(d)} قطر رینگ به اینچ است؛ حرف R نشان‌دهندهٔ ساختار رادیال است.")
    m = re.fullmatch(r"(\d{3,4})R(\d{2})", s)
    if m:
        w, d = m.groups()
        return (f"در سایز {size}، عرض لاستیک حدود {fa(int(w) / 100)} اینچ و قطر رینگ {fa(d)} اینچ است؛ "
                f"حرف R نشان‌دهندهٔ ساختار رادیال است.")
    m = re.fullmatch(r"(\d{3,4})-(\d{2})", s)
    if m:
        w, d = m.groups()
        return f"در سایز {size}، عرض لاستیک حدود {fa(int(w) / 100)} اینچ و قطر رینگ {fa(d)} اینچ است."
    return None


def size_facts(size):
    """اعداد قابل‌محاسبه از خود سایز (اسمی/تقریبی). برای الگوی ناشناخته None."""
    s = (size or "").strip().upper().replace(" ", "")
    m = re.fullmatch(r"(\d{3})/(\d{2})R(\d{2})", s)
    if m:
        w, r, d = map(int, m.groups())
        side = round(w * r / 100)
        return {"metric": True, "width_mm": w, "rim_in": d, "side_mm": side, "diam_mm": round(d * 25.4 + 2 * side)}
    m = re.fullmatch(r"(\d{3,4})(?:R|-)(\d{2})", s)
    if m:
        w, d = int(m.group(1)), int(m.group(2))
        return {"metric": False, "width_in": w / 100, "width_mm": round(w / 100 * 25.4), "rim_in": d}
    return None


def num(x):
    return fa(f"{x:g}")


def size_spec_rows(size):
    f = size_facts(size)
    if not f:
        return []
    rows = [("قطر رینگ", f"{num(f['rim_in'])} اینچ")]
    if f["metric"]:
        rows += [("عرض مقطع", f"{num(f['width_mm'])} میلی‌متر"),
                 ("ارتفاع دیواره (تقریبی)", f"{num(f['side_mm'])} میلی‌متر"),
                 ("قطر کلی (تقریبی)", f"{num(f['diam_mm'])} میلی‌متر")]
    else:
        rows.append(("عرض اسمی", f"{num(f['width_in'])} اینچ (حدود {num(f['width_mm'])} میلی‌متر)"))
    return rows


def _norm_size(s):
    return (s or "").strip().upper().replace(" ", "")


def catalog_pages(products):
    return [q for q in products if q.get("page") is not False and q.get("link")]


def link_item(q, label):
    return f'<li><a href="{esc(q["link"])}" class="text-decoration-none gt-tap">{esc(label)}</a></li>'


def catalog_sections(p, products):
    """بخش‌هایی که فقط از داده‌های واقعی کاتالوگ ساخته می‌شوند و برای هر صفحه متفاوت‌اند."""
    pool = [q for q in catalog_pages(products) if q["id"] != p["id"]]
    size, brand, veh = _norm_size(p.get("size")), p.get("brand", "").strip(), vehicle_label(p.get("vehicle", ""))
    out = []
    # همین سایز با برند/خودروی دیگر
    same = [q for q in pool if _norm_size(q.get("size")) == size]
    if same:
        items = [link_item(q, " — ".join(x for x in (f"برند {q.get('brand','').strip()}", vehicle_label(q.get("vehicle", ""))) if x)) for q in same]
        out.append('<h3 class="h6 fw-bold text-dark mt-4 mb-2">همین سایز با برند یا خودروی دیگر:</h3>\n<ul class="mb-3">\n' + "\n".join(items) + "\n</ul>")
    # سایزهای دیگر همین برند
    seen, items = set(), []
    for q in sorted(pool, key=lambda q: q["category"] != p["category"]):
        if q.get("brand", "").strip() == brand and _norm_size(q.get("size")) != size and _norm_size(q.get("size")) not in seen:
            seen.add(_norm_size(q.get("size")))
            items.append(link_item(q, f"{q.get('size','').strip()} — {vehicle_label(q.get('vehicle', '')) or q.get('brand','').strip()}"))
    if items:
        out.append(f'<h3 class="h6 fw-bold text-dark mt-4 mb-2">سایزهای دیگر برند {esc(brand)} در کاتالوگ:</h3>\n<ul class="mb-3">\n' + "\n".join(items[:6]) + "\n</ul>")
    # سایزهای دیگر همین خودرو
    if veh:
        seen, items = {size}, []
        for q in pool:
            if vehicle_label(q.get("vehicle", "")) == veh and _norm_size(q.get("size")) not in seen:
                seen.add(_norm_size(q.get("size")))
                items.append(link_item(q, f"{q.get('size','').strip()} — برند {q.get('brand','').strip()}"))
        if items:
            out.append(f'<h3 class="h6 fw-bold text-dark mt-4 mb-2">سایزهای دیگر ثبت‌شده برای {esc(veh)}:</h3>\n<ul class="mb-3">\n' + "\n".join(items[:6]) + "\n</ul>")
    return out


def diameter_comparison(p, products):
    """مقایسهٔ قطر کلی با سایزهای هم‌رینگ در کاتالوگ؛ فقط محاسبهٔ ریاضی از خود سایز (تقریبی)."""
    f = size_facts(p.get("size"))
    if not f or not f["metric"]:
        return None
    seen, rows = {_norm_size(p.get("size"))}, []
    for q in catalog_pages(products):
        fq = size_facts(q.get("size"))
        key = _norm_size(q.get("size"))
        if not fq or not fq["metric"] or fq["rim_in"] != f["rim_in"] or key in seen:
            continue
        seen.add(key)
        diff = fq["diam_mm"] - f["diam_mm"]
        pct = diff / f["diam_mm"] * 100
        rows.append((abs(diff), q, diff, pct))
    if not rows:
        return None
    rows.sort(key=lambda r: r[0])
    items = []
    for _, q, diff, pct in rows[:3]:
        word = "بزرگ‌تر" if diff > 0 else ("کوچک‌تر" if diff < 0 else "هم‌اندازه")
        gap = "" if diff == 0 else f" (حدود {num(abs(diff))} میلی‌متر و {fa(f'{abs(pct):.1f}')}٪ {word})"
        items.append(link_item(q, f"{q.get('size','').strip()} — {vehicle_label(q.get('vehicle',''))}{gap}"))
    return ('<h3 class="h6 fw-bold text-dark mt-4 mb-2">مقایسه قطر کلی با سایزهای هم‌رینگ (تقریبی):</h3>\n'
            f'<p>قطر کلی {esc(p.get("size","").strip())} حدود {num(f["diam_mm"])} میلی‌متر است. اختلاف قطر کلی با سایزهای نزدیک در کاتالوگ:</p>\n'
            '<ul class="mb-3">\n' + "\n".join(items) + '\n</ul>\n'
            '<p class="small">این اعداد محاسبهٔ اسمی از روی خود سایز است؛ اختلاف زیاد قطر کلی روی کیلومترشمار و فاصلهٔ لاستیک تا گلگیر اثر می‌گذارد؛ پیش از تغییر سایز، آن را با سایز استاندارد خودرو مقایسه کنید.</p>')


def render_wholesale_options(products):
    """گزینه‌های انتخاب مدل در فرم فروش عمده (دسته‌بندی‌شده، از products.json)."""
    out = []
    for cat in (5, 6, 7, 8):
        items = [p for p in catalog_pages(products) if int(p["category"]) == cat]
        if not items:
            continue
        out.append(f'<optgroup label="{esc(CAT_INFO[cat][0])}">')
        for p in sorted(items, key=lambda q: (_norm_size(q.get("size")), q.get("brand", ""))):
            label = " — ".join(x for x in (p.get("size", "").strip(), vehicle_label(p.get("vehicle", "")),
                                           f"برند {p.get('brand', '').strip()}") if x)
            out.append(f'<option value="{esc(Path(p["link"]).stem)}">{esc(label)}</option>')
        out.append("</optgroup>")
    return "\n".join(out)


def vehicle_label(v):
    return (v or "").replace(" – ", " و ").replace("–", " و ").strip()


def ul(items):
    return '<ul class="mb-3">\n' + "\n".join(f"<li>{esc(i)}</li>" for i in items) + "\n</ul>"


def _size_guide_published():
    try:
        return any(a.get("id") == "size-guide" for a in json.loads(read("articles.json")))
    except Exception:
        return False


SIZE_GUIDE_PUBLISHED = _size_guide_published()


def build_caption(p, products=None):
    title = product_title(p)
    main_t = title.partition(" | ")[0]
    size = p.get("size", "").strip()
    brand = p.get("brand", "").strip()
    cat = int(p.get("category", 5))
    cat_name, use, who = CAT_INFO.get(cat, CAT_INFO[5])
    veh = vehicle_label(p.get("vehicle", ""))
    parts = []

    # ۱) کپشن سفارشی (اگر در products.json نوشته شده باشد)
    custom = (p.get("caption") or "").strip()
    if custom:
        parts.append(f'<h3 class="h6 fw-bold text-dark mt-2 mb-2">{esc(main_t)}</h3>')
        parts += [f"<p>{esc(x.strip())}</p>" for x in custom.split("\n") if x.strip()]
    else:
        target = f"برای {veh}" if veh and cat != 8 else (veh or who)
        parts.append(f'<h3 class="h6 fw-bold text-dark mt-2 mb-2">{esc(main_t)}؛ مناسب {esc(use)}</h3>')
        parts.append(f"<p>{esc(main_t)} با برند <strong>{esc(brand)}</strong> در گهرتایر خرم‌آباد عرضه می‌شود. "
                     f"این سایز {esc(target)} کاربرد دارد و برای {esc(use)} انتخاب می‌شود.</p>")
    exp = explain_size(size) if size else None
    if exp:
        parts.append(f"<p>{esc(exp)}</p>")

    # ۲) مناسب برای
    fits = p.get("fits")   # فقط اطلاعات واقعی ثبت‌شده؛ تکرار نام خودرو (که در متن بالا هست) لازم نیست
    if fits:
        parts.append('<h3 class="h6 fw-bold text-dark mt-4 mb-2">مناسب برای:</h3>')
        parts.append(ul(fits))
    feats = p.get("features")
    if feats:
        parts.append('<h3 class="h6 fw-bold text-dark mt-4 mb-2">ویژگی‌ها:</h3>')
        parts.append(ul(feats))

    # ۳) اطلاعات واقعی کاتالوگ (متفاوت برای هر صفحه)
    if products:
        parts += catalog_sections(p, products)
        cmp_html = diameter_comparison(p, products)
        if cmp_html:
            parts.append(cmp_html)

    # ۴) جملهٔ کوتاه راهنمای خرید (لینک به مقالهٔ سایز اگر منتشر شده باشد)
    guide = ('برای مطمئن‌شدن از سایز، <a href="articles/size-guide.html" class="text-decoration-none">راهنمای خواندن سایز لاستیک</a> را ببینید؛ '
             if SIZE_GUIDE_PUBLISHED else "سایز را با برچسب داخل درِ راننده یا دفترچهٔ خودرو تطبیق دهید؛ ")
    parts.append(f"<p>{guide}تاریخ تولید (کد DOT) را هنگام تحویل بررسی کنید و قیمت و موجودی روز را با تماس یا واتساپ استعلام کنید.</p>")
    return "\n".join(parts)


def product_related(p, products, n=4):
    cat, veh, size = p["category"], p.get("vehicle", ""), p.get("size", "")
    pool = [q for q in products if q["id"] != p["id"] and q.get("link") and q.get("page") is not False]

    def score(q):
        return (q.get("size") == size) * 4 + (q.get("vehicle") == veh) * 2 + (q["category"] == cat)
    pool = [q for q in pool if q["category"] == cat] or pool
    pool.sort(key=lambda q: -score(q))
    return pool[:n]


def render_related(p, products):
    rel = product_related(p, products)
    if not rel:
        return ""
    cards = []
    for q in rel:
        t = product_title(q)
        cards.append(f'''            <div class="col">
                <div class="card h-100 border-0 shadow-sm rounded-4 card-product bg-white">
                    <a href="{esc(q['link'])}" class="text-decoration-none">
                        <div class="text-center bg-light rounded-top-4 p-3 position-relative overflow-hidden" style="height: 180px; display: flex; align-items: center; justify-content: center;">
                            <img src="{esc(q['image'])}" alt="{esc(t)}" style="max-height: 150px; object-fit: contain;" class="transition-transform w-100">
                        </div>
                    </a>
                    <div class="card-body d-flex flex-column p-4">
                        <a href="{esc(q['link'])}" class="text-decoration-none">
                            <h3 class="h6 fw-bold mb-3 text-dark text-truncate-2" style="line-height: 1.5;">{esc(t.partition(" | ")[0])}</h3>
                        </a>
                        <div class="mt-auto d-flex justify-content-between align-items-center pt-3 border-top">
                            <span class="fw-extrabold text-digi" style="font-size:.85rem">استعلام قیمت</span>
                            <a href="{esc(q['link'])}" class="btn btn-sm btn-light rounded-circle p-2 d-flex align-items-center justify-content-center text-dark" style="width: 35px; height: 35px;" aria-label="مشاهدهٔ {esc(t.partition(" | ")[0])}">
                                <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>''')
    return ('''    <div class="mb-5 mt-5">
        <h2 class="h4 fw-bold mb-4 text-dark d-flex align-items-center">
            <i class="fa-solid fa-layer-group text-digi ms-2 fs-5" aria-hidden="true"></i> محصولات مرتبط و پیشنهادی
        </h2>
        <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
''' + "\n".join(cards) + "\n        </div>\n    </div>")


def product_slug(p):
    """اسلاگ پایدار و مرتبط با خود محصول؛ برای محصولات جدید ترجیحاً نام تصویر/محصول را دنبال می‌کند."""
    slug = str(p.get("slug") or "").strip()
    if not slug:
        image = str(p.get("image") or "").strip()
        if image:
            slug = Path(image).stem
    if not slug:
        parts = [p.get("vehicle", ""), p.get("size", ""), p.get("brand", "")]
        slug = "-".join(x for x in parts if str(x).strip())
    slug = slug.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9_-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or f"product-{p['id']}"


def page_name(p):
    return f"products/{product_slug(p)}.html"


def product_meta(p):
    """(عنوان صفحه، توضیح متا، نام کوتاه) — مشترک بین صفحه‌های تولیدشده و صفحه‌های قدیمی محصول."""
    main_t = product_title(p).partition(" | ")[0]
    brand = p.get("brand", "").strip()
    _, use, _ = CAT_INFO.get(int(p["category"]), CAT_INFO[5])
    warranty = "۲ سال ضمانت کتبی" in (p.get("description") or "")   # فقط اگر در داده‌ها ذکر شده باشد
    tail = "؛ با ۲ سال ضمانت کتبی. استعلام قیمت و موجودی با تماس یا واتساپ." if warranty else "؛ استعلام قیمت و موجودی با تماس یا واتساپ."
    return f"{main_t} | {brand} | گهرتایر", f"{main_t} برند {brand} در گهرتایر خرم‌آباد. مناسب {use}{tail}", main_t


def generate_product_pages(products):
    """برای هر محصول (به‌جز page=false) صفحه‌ای در products/<slug>.html می‌سازد و link را تنظیم می‌کند.
    اگر فایل همان نام وجود داشته باشد و نشانگر @@generated-product نداشته باشد، صفحهٔ دستی است و دست نمی‌خورد."""
    tpl = read("templates/product.html")
    keep = set()
    for p in products:
        if p.get("page") is False:
            continue
        p["link"] = page_name(p)
        if os.path.exists(p["link"]) and "@@generated-product" not in read(p["link"])[:200]:
            continue
        p["_generated"] = True
    for p in products:
        if not p.get("_generated"):
            continue
        title = product_title(p)
        main_t = title.partition(" | ")[0]
        size, brand, cat = p.get("size", ""), p.get("brand", ""), int(p["category"])
        cat_name, use, _ = CAT_INFO.get(cat, CAT_INFO[5])
        veh = vehicle_label(p.get("vehicle", ""))
        available = bool(p.get("available", True))
        lead = f"{main_t} از برند {brand}؛ مناسب {use}. قیمت و موجودی روز را با تماس یا واتساپ استعلام کنید."
        seo_title, meta, _ = product_meta(p)
        stock = ('<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill fw-bold">'
                 '<i class="fa-solid fa-circle-check ms-1" aria-hidden="true"></i> موجود؛ برای استعلام تماس بگیرید</span>') if available else \
                ('<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-2 rounded-pill fw-bold">'
                 '<i class="fa-solid fa-clock ms-1" aria-hidden="true"></i> استعلام موجودی</span>')
        rows = [("سایز", f'<span dir="ltr">{esc(size)}</span>')]
        if veh:
            rows.append(("خودرو / کاربرد", esc(veh)))
        rows += [(k, esc(v)) for k, v in size_spec_rows(size)]
        rows += [("برند", esc(brand)), ("دسته", esc(cat_name)),
                 ("وضعیت", "موجود؛ استعلام با تماس" if available else "استعلام موجودی"),
                 ("قیمت", "استعلام با تماس")]
        spec_rows = "\n".join(f'            <dt class="col-5 col-sm-3">{k}</dt>\n            <dd class="col-7 col-sm-9">{v}</dd>' for k, v in rows)
        wa = "https://wa.me/989120346053?text=" + urllib.parse.quote(f"سلام، درباره {main_t} ({brand}) سؤال دارم.")
        cat_cfg = CATEGORY_LANDINGS.get(cat)
        category_crumb = ""
        if cat_cfg:
            category_crumb = (f'            <li class="breadcrumb-item">\n'
                               f'                <a href="categories/{esc(cat_cfg["slug"])}.html" class="text-decoration-none text-muted fw-semibold transition-hover">{esc(cat_cfg["short"])}</a>\n'
                               f'            </li>')
        vals = {"title": esc(seo_title), "meta_description": esc(meta),
                "h1": esc(main_t), "image": esc(p["image"]), "alt": esc(title), "code": esc(p["id"].upper()),
                "stock_badge": stock, "lead": esc(lead), "wa_url": esc(wa), "spec_rows": spec_rows,
                "category_crumb": category_crumb, "slug": esc(product_slug(p)),
                "caption_html": build_caption(p, products), "related_html": render_related(p, products)}
        out = tpl
        out = re.sub(r"\{\{(\w+)\}\}", lambda m: vals.get(m.group(1), m.group(0)), out)
        write(page_name(p), out)
        keep.add(page_name(p))
    # صفحه‌های تولیدشدهٔ قدیمی که دیگر محصولی ندارند پاک می‌شوند
    for f in pages_in("products/*.html"):
        if f not in keep and "@@generated-product" in read(f)[:200]:
            os.remove(f)
    todo = {}
    for p in products:
        if p.get("_generated") and not (p.get("caption") or p.get("fits") or p.get("features")):
            todo.setdefault(_norm_size(p.get("size")), []).append(p["id"])
    n_todo = sum(len(v) for v in todo.values())
    if n_todo:
        print(f"!! {n_todo} صفحهٔ محصول caption/fits واقعی ندارند (فقط اطلاعات کاتالوگ نمایش داده می‌شود). "
              "برای ایندکس بهتر، برای سایزهای پرتکرار این‌ها را در products.json بنویسید:")
        for sz, ids in sorted(todo.items(), key=lambda kv: -len(kv[1]))[:8]:
            print(f"   {sz}: {len(ids)} محصول ({', '.join(ids)})")
    print(f"product pages generated: {len(keep)}")



def fa_date(iso):
    """تاریخ میلادی ساده (YYYY-MM-DD) را برای نمایش برمی‌گرداند؛ بدون تبدیل تقویم."""
    try:
        d = datetime.date.fromisoformat(str(iso))
        return d.strftime("%Y/%m/%d")
    except Exception:
        return esc(iso)


def article_slug(a):
    slug = str(a.get("id") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9_-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "article"


def article_link(a):
    return f"articles/{article_slug(a)}.html"


def render_article_card(a):
    link = article_link(a)
    cat = esc(a.get("category", "راهنمای خرید"))
    title = esc(a.get("title", ""))
    intro = esc(a.get("intro", ""))
    return f'''        <div class="col">
            <div class="card h-100 border-0 shadow-sm rounded-4 bg-white">
                <a href="{esc(link)}" class="text-decoration-none">
                    <div class="card-body d-flex flex-column p-4">
                        <span class="badge bg-light text-danger border px-3 py-2 rounded-pill mb-3 align-self-start" style="font-size:.75rem">{cat}</span>
                        <h2 class="h6 fw-bold mb-2 text-dark">{title}</h2>
                        <p class="text-secondary small mb-0 text-truncate-2">{intro}</p>
                    </div>
                </a>
            </div>
        </div>'''


def render_related_articles(current, articles, n=3):
    pool = [a for a in articles if a.get("id") != current.get("id")]
    pool.sort(key=lambda a: a.get("category") != current.get("category"))
    rel = pool[:n]
    if not rel:
        return ""
    cards = "\n".join(render_article_card(a) for a in rel)
    return ('    <section class="mb-5">\n'
            '        <h2 class="h5 fw-bold mb-4 text-dark">مقالات مرتبط</h2>\n'
            '        <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-4">\n'
            f'{cards}\n'
            '        </div>\n'
            '    </section>')


def generate_article_pages(articles):
    """صفحهٔ اختصاصی برای هر آیتم articles.json + صفحهٔ فهرست articles.html می‌سازد."""
    if not os.path.exists("templates/article.html"):
        return
    tpl = read("templates/article.html")
    keep = set()
    for a in articles:
        link = article_link(a)
        vals = {
            "title": esc(f"{a.get('title','')} | گهرتایر"),
            "meta_description": esc(a.get("meta_description", "")),
            "h1": esc(a.get("title", "")),
            "category_label": esc(a.get("category", "راهنمای خرید")),
            "updated_fa": fa_date(a.get("updated", "")),
            "body_html": a.get("body_html", ""),
            "related_articles_html": render_related_articles(a, articles),
        }
        out = re.sub(r"\{\{(\w+)\}\}", lambda m: vals.get(m.group(1), m.group(0)), tpl)
        write(link, out)
        keep.add(link)
    # صفحه‌های مقالهٔ قدیمی که دیگر در articles.json نیستند حذف می‌شوند
    for f in pages_in("articles/*.html"):
        if f not in keep and "@@generated-article" in read(f)[:200]:
            os.remove(f)

    if os.path.exists("templates/articles.html"):
        list_tpl = read("templates/articles.html")
        cards = "\n".join(render_article_card(a) for a in articles) if articles else \
            '        <p class="text-secondary">به‌زودی اولین مقاله منتشر می‌شود.</p>'
        list_vals = {
            "title": "راهنمای خرید لاستیک | گهرتایر خرم‌آباد",
            "meta_description": "مقالات و راهنماهای خرید لاستیک گهرتایر خرم‌آباد؛ انتخاب سایز، نگهداری و زمان تعویض لاستیک.",
            "h1": "راهنمای خرید لاستیک",
            "intro": "مجموعه مقالات گهرتایر خرم‌آباد برای انتخاب درست لاستیک، خواندن سایز روی دیواره و نگهداری صحیح آن.",
            "articles_html": cards,
        }
        out = re.sub(r"\{\{(\w+)\}\}", lambda m: list_vals.get(m.group(1), m.group(0)), list_tpl)
        write("articles.html", out)
    print(f"article pages generated: {len(keep)}")


def generate_category_pages(products):
    """چهار صفحه فرود سئو-محور برای دسته‌های اصلی فروشگاه می‌سازد."""
    tpl = read("templates/category.html")
    made = []
    for cat, cfg in CATEGORY_LANDINGS.items():
        items = [p for p in products if int(p.get("category", 5)) == cat and p.get("link") and p.get("page") is not False]
        summary = f"{len(items)} محصول شامل سایزها و برندهای ثبت‌شده در این دسته. برای هر محصول صفحه اختصاصی و اطلاعات پایه در دسترس است."
        vals = {"title": esc(cfg["title"]), "meta_description": esc(cfg["description"]), "h1": esc(cfg["h1"]),
                "intro": esc(cfg["intro"]), "category_summary": esc(summary), "short_name": esc(cfg["short"]),
                "count": fa(len(items)), "products_html": render_products(items)}
        out = re.sub(r"\{\{(\w+)\}\}", lambda m: vals.get(m.group(1), m.group(0)), tpl)
        write(f"categories/{cfg['slug']}.html", out)
        made.append(f"categories/{cfg['slug']}.html")
    print(f"category pages generated: {len(made)}")


def is_redirect_stub(text):
    return "@@redirect-stub" in text or ('http-equiv="refresh"' in text and "noindex,follow" in text and len(text) < 2000)


def write_redirect_pages():
    """آدرس‌های قدیمی (redirects.json) را به آدرس جدید می‌فرستد.
    پیش‌فرض: صفحهٔ کوچک redirect در همان آدرس قدیمی (روی هر هاستی کار می‌کند).
    اگر در seo.json مقدار "redirect_stubs": false بگذارید، آن صفحه‌ها حذف می‌شوند و به‌جایشان
    فایل‌های _redirects (Netlify/Cloudflare) و redirects-apache.txt (برای .htaccess) ساخته می‌شود."""
    stubs = bool(SEO.get("redirect_stubs", True))
    for src_page, dst in REDIRECTS.items():
        if not os.path.exists(dst):
            raise ValueError(f"مقصد redirect وجود ندارد: {src_page} ← {dst}")
        path = Path(src_page)
        if not stubs:
            if path.exists() and is_redirect_stub(read(src_page)):
                path.unlink()
            continue
        target = f"{SITE_URL}/{dst}" if SITE_URL else dst
        out = f"""<!-- @@redirect-stub: خروجی build.py از redirects.json؛ دستی ویرایش نکنید -->
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="robots" content="noindex,follow">
  <link rel="canonical" href="{esc(target)}">
  <meta http-equiv="refresh" content="0;url={esc(dst)}">
  <title>در حال انتقال | گهرتایر خرم‌آباد</title>
</head>
<body>
  <p>این صفحه منتقل شد. <a href="{esc(dst)}">مشاهده صفحهٔ جدید</a></p>
</body>
</html>
"""
        write(src_page, out)
    # redirect قدیمی که دیگر در redirects.json نیست پاک شود
    for f in pages_in("*.html"):
        if f not in REDIRECTS and is_redirect_stub(read(f)):
            os.remove(f)
    if stubs:
        for f in ("_redirects", "redirects-apache.txt"):
            if os.path.exists(f):
                os.remove(f)
    else:
        write("_redirects", "\n".join(f"/{a} /{b} 301" for a, b in REDIRECTS.items()) + "\n")
        write("redirects-apache.txt", "\n".join(f"Redirect 301 /{a} /{b}" for a, b in REDIRECTS.items()) + "\n")


def validate_catalog(products):
    required = {"id", "vehicle", "size", "brand", "category", "image", "available"}
    ids=set()
    for p in products:
        missing=required - set(p)
        if missing:
            raise ValueError(f"محصول {p!r} فیلدهای لازم را ندارد: {', '.join(sorted(missing))}")
        if p["id"] in ids:
            raise ValueError(f"شناسه تکراری محصول: {p['id']}")
        ids.add(p["id"])
        if int(p["category"]) not in {5,6,7,8}:
            raise ValueError(f"دسته‌بندی نامعتبر برای {p['id']}: {p['category']}")
    slugs = {}
    for p in products:
        if p.get("page") is False:
            continue
        s = product_slug(p)
        if s in slugs:
            raise ValueError(f"اسلاگ تکراری «{s}» برای {slugs[s]} و {p['id']}؛ به یکی از آن‌ها فیلد slug یکتا بدهید.")
        slugs[s] = p["id"]


def render_products(products):
    return "\n".join(render_product_card(p) for p in products)


# ---------------------------------------------------------------------------
# سئو: canonical، Open Graph، داده ساختاریافته (JSON-LD)، sitemap.xml، robots.txt
# تنظیمات در seo.json؛ بدون site_url فقط عنوان/توضیح و schemaهای بدون آدرس ساخته می‌شوند.
# ---------------------------------------------------------------------------
SEO = json.loads(read("seo.json"))
SITE_URL = (os.environ.get("SITE_URL") or SEO.get("site_url") or "").strip().rstrip("/")
SEO_PAGES = SEO.get("pages", {})
SEO_SKIP = set()  # بعد از ساخت صفحات محصول، با redirectهای واقعی کامل می‌شود.
LASTMOD_FILE = "seo-lastmod.json"  # تاریخ آخرین تغییر واقعی هر صفحه (برای lastmod درست در sitemap)
SEO_WARNINGS = []


def page_url(page):
    if not SITE_URL:
        return None
    return SITE_URL + "/" if page == "index.html" else f"{SITE_URL}/{page}"


def abs_asset(path):
    return f"{SITE_URL}/{path.lstrip('/')}" if SITE_URL else None


def ws(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def head_title_desc(s):
    t = re.search(r"<title>(.*?)</title>", s, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', s)
    return ws(t.group(1)) if t else "", html.unescape(d.group(1)).strip() if d else ""


def h1_text(s):
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", s, re.S)
    return ws(m.group(1)) if m else ""


def set_title_desc(s, title, desc):
    s = re.sub(r"<title>.*?</title>", lambda _: f"<title>{esc(title)}</title>", s, count=1, flags=re.S)
    if not desc:
        return s
    tag = f'<meta name="description" content="{esc(desc)}">'
    if re.search(r'<meta name="description"[^>]*>', s):
        return re.sub(r'<meta name="description"[^>]*>', lambda _: tag, s, count=1)
    return s.replace("</title>", "</title>\n    " + tag, 1)


def ld_script(obj):
    body = json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'


def og_image(path):
    """(آدرس مطلق، عرض، ارتفاع) برای تصویر؛ JPG/PNG اصلی را به WebP ترجیح می‌دهد (سازگاری بهتر با تلگرام/واتساپ)."""
    if not SITE_URL or not path or not os.path.exists(path):
        return None
    w = h = None
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        pass
    return abs_asset(path), w, h


def business_node():
    b = SEO["business"]
    node = {"@type": b.get("type", "LocalBusiness"), "name": b["name"], "description": b.get("description", ""),
            "telephone": b["phone"],
            "address": {"@type": "PostalAddress", "addressLocality": b["city"], "streetAddress": b["street"],
                        "addressCountry": b.get("country", "IR")},
            "areaServed": {"@type": "City", "name": b["city"]}}
    if b.get("hours"):
        node["openingHoursSpecification"] = [{"@type": "OpeningHoursSpecification", "dayOfWeek": b["hours"]["days"],
                                              "opens": b["hours"]["opens"], "closes": b["hours"]["closes"]}]
    if b.get("same_as"):
        node["sameAs"] = b["same_as"]
    if b.get("geo"):
        node["geo"] = {"@type": "GeoCoordinates", "latitude": b["geo"]["lat"], "longitude": b["geo"]["lng"]}
    if SITE_URL:
        node["@id"] = SITE_URL + "/#business"
        node["url"] = SITE_URL + "/"
        img = og_image(SEO.get("default_og_image", ""))
        if img:
            node["image"] = img[0]
    return node


def breadcrumb_ld(items):
    """items: [(نام، آدرس مطلق)]؛ بدون SITE_URL ساخته نمی‌شود چون آیتم‌ها آدرس لازم دارند."""
    if not SITE_URL:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(items, 1)]}


def build_seo_block(page, s, prod, products_by_page, catalog):
    title, desc = head_title_desc(s)
    h1 = h1_text(s) or title
    lines, ld = [], []
    crumb_home = ("خانه", SITE_URL + "/") if SITE_URL else None

    # --- تصویر اشتراک‌گذاری ---
    img = og_image(prod["image"]) if prod else og_image(SEO.get("default_og_image", ""))
    if SITE_URL and not img and not prod and "og-missing" not in SEO_WARNINGS:
        SEO_WARNINGS.append("og-missing")
        print(f"!! تصویر پیش‌فرض اشتراک‌گذاری پیدا نشد ({SEO.get('default_og_image')}). "
              "یک تصویر 1200×630 بگذارید تا لینک‌ها در تلگرام/واتساپ/اینستاگرام با تصویر نمایش داده شوند.")

    if SITE_URL:
        url = page_url(page)
        lines.append(f'<link rel="canonical" href="{esc(url)}">')
        lines += [f'<meta property="og:locale" content="{esc(SEO.get("locale", "fa_IR"))}">',
                  f'<meta property="og:site_name" content="{esc(SEO["site_name"])}">',
                  f'<meta property="og:type" content="{"product" if prod else "website"}">',
                  f'<meta property="og:title" content="{esc(title)}">',
                  f'<meta property="og:description" content="{esc(desc)}">',
                  f'<meta property="og:url" content="{esc(url)}">']
        card = "summary"
        if img:
            lines.append(f'<meta property="og:image" content="{esc(img[0])}">')
            if img[1] and img[2]:
                lines += [f'<meta property="og:image:width" content="{img[1]}">', f'<meta property="og:image:height" content="{img[2]}">']
                if img[1] >= img[2] * 1.3:
                    card = "summary_large_image"
            lines.append(f'<meta property="og:image:alt" content="{esc(h1)}">')
        lines += [f'<meta name="twitter:card" content="{card}">', f'<meta name="twitter:title" content="{esc(title)}">',
                  f'<meta name="twitter:description" content="{esc(desc)}">']
        if img:
            lines.append(f'<meta name="twitter:image" content="{esc(img[0])}">')

    # --- داده ساختاریافته ---
    crumb_name = SEO_PAGES.get(page, {}).get("crumb")
    if page == "index.html":
        if SITE_URL:
            ld.append({"@context": "https://schema.org", "@type": "WebSite", "@id": SITE_URL + "/#website", "url": SITE_URL + "/",
                       "name": SEO["site_name"], "inLanguage": "fa", "publisher": {"@id": SITE_URL + "/#business"}})
        ld.append({"@context": "https://schema.org", **business_node()})
    elif page == "contact.html":
        ld.append({"@context": "https://schema.org", **business_node()})
        bc = breadcrumb_ld([crumb_home, (crumb_name, page_url(page))]) if SITE_URL else None
        if bc: ld.append(bc)
    elif page == "products.html":
        bc = breadcrumb_ld([crumb_home, (crumb_name, page_url(page))]) if SITE_URL else None
        if bc: ld.append(bc)
        if SITE_URL:
            items = [q for q in catalog if q.get("link") and q.get("page") is not False]
            ld.append({"@context": "https://schema.org", "@type": "ItemList", "name": h1 or title,
                       "numberOfItems": len(items),
                       "itemListElement": [{"@type": "ListItem", "position": i, "name": product_title(q).partition(" | ")[0],
                                            "url": page_url(q["link"])} for i, q in enumerate(items, 1)]})
    elif page.startswith("categories/"):
        slug = page[len("categories/"):-len(".html")]
        cat = CATEGORY_BY_SLUG.get(slug)
        cfg = CATEGORY_LANDINGS.get(cat)
        items = [q for q in catalog if cat and int(q.get("category", 5)) == cat and q.get("link") and q.get("page") is not False]
        if SITE_URL and cfg:
            ld.append({"@context": "https://schema.org", "@type": "CollectionPage", "name": h1,
                       "url": page_url(page), "description": desc, "inLanguage": "fa"})
            ld.append({"@context": "https://schema.org", "@type": "ItemList", "name": h1,
                       "numberOfItems": len(items),
                       "itemListElement": [{"@type": "ListItem", "position": i,
                                            "name": product_title(q).partition(" | ")[0],
                                            "url": page_url(q["link"])} for i, q in enumerate(items, 1)]})
            bc = breadcrumb_ld([crumb_home, ("فروشگاه", page_url("products.html")), (h1, page_url(page))])
            if bc: ld.append(bc)
    elif prod:
        cat_name = CAT_INFO.get(int(prod["category"]), CAT_INFO[5])[0]
        node = {"@context": "https://schema.org", "@type": "Product", "name": h1, "sku": prod["id"],
                "brand": {"@type": "Brand", "name": prod.get("brand", "").strip()}, "category": cat_name, "description": desc}
        size = prod.get("size", "").strip()
        vehicle = vehicle_label(prod.get("vehicle", ""))
        props = []
        if size: props.append({"@type": "PropertyValue", "name": "سایز لاستیک", "value": size})
        if vehicle: props.append({"@type": "PropertyValue", "name": "خودرو / کاربرد", "value": vehicle})
        if props: node["additionalProperty"] = props
        if SITE_URL:
            node["url"] = page_url(page)
            if img: node["image"] = img[0]
        # Offer فقط وقتی قیمت واقعی در products.json ثبت شده باشد ساخته می‌شود.
        if prod.get("price") is not None and str(prod.get("price")).strip() != "":
            node["offers"] = {"@type": "Offer", "price": str(prod["price"]),
                               "priceCurrency": prod.get("priceCurrency", "IRR"),
                               "availability": "https://schema.org/InStock" if prod.get("available", True) else "https://schema.org/OutOfStock",
                               "url": page_url(page) if SITE_URL else prod.get("link")}
        ld.append(node)
        cat_cfg = CATEGORY_LANDINGS.get(int(prod["category"]))
        crumbs = [crumb_home, ("فروشگاه", page_url("products.html"))]
        if cat_cfg:
            crumbs.append((cat_cfg["short"], page_url(f"categories/{cat_cfg['slug']}.html")))
        crumbs.append((h1, page_url(page)))
        bc = breadcrumb_ld(crumbs) if SITE_URL else None
        if bc: ld.append(bc)
    elif page == "articles.html":
        if SITE_URL:
            bc = breadcrumb_ld([crumb_home, ("راهنمای خرید", page_url(page))])
            if bc: ld.append(bc)
    elif page.startswith("articles/") and page in articles_by_page:
        art = articles_by_page[page]
        if SITE_URL:
            ld.append({"@context": "https://schema.org", "@type": "Article", "headline": h1,
                       "description": desc, "url": page_url(page), "inLanguage": "fa",
                       "datePublished": art.get("updated", ""), "dateModified": art.get("updated", ""),
                       "publisher": {"@id": SITE_URL + "/#business"}})
            bc = breadcrumb_ld([crumb_home, ("راهنمای خرید", page_url("articles.html")), (h1, page_url(page))])
            if bc: ld.append(bc)
    elif crumb_name and SITE_URL:
        ld.append(breadcrumb_ld([crumb_home, (crumb_name, page_url(page))]))

    lines += [ld_script(x) for x in ld]
    if not lines:
        return "<!-- @@seo:start -->\n    <!-- @@seo:end -->"
    return "<!-- @@seo:start -->\n    " + "\n    ".join(lines) + "\n    <!-- @@seo:end -->"


def apply_seo(page, s, prod, products_by_page, catalog):
    s = re.sub(r"[ \t]*<!-- @@seo:start -->.*?<!-- @@seo:end -->\n?", "", s, flags=re.S)
    block = build_seo_block(page, s, prod, products_by_page, catalog)
    return s.replace("</head>", "    " + block + "\n</head>", 1)


def write_robots_and_sitemap(pages, contents, products_by_page):
    lines = ["User-agent: *", "Allow: /", "Disallow: /404.html", "Disallow: /tools/", "Disallow: /templates/",
             "Disallow: /partials/", "Disallow: /*.md$", ""]
    if SITE_URL:
        lines.append(f"Sitemap: {SITE_URL}/sitemap.xml")
    else:
        print("!! site_url در seo.json خالی است؛ sitemap.xml و canonical ساخته نشد و خط Sitemap در robots.txt نیست.")
    write("robots.txt", "\n".join(lines).rstrip() + "\n")
    if not SITE_URL:
        if os.path.exists("sitemap.xml"):
            os.remove("sitemap.xml")
        return
    try:
        state = json.loads(read(LASTMOD_FILE))
    except Exception:
        state = {}
    today = datetime.date.today().isoformat()
    new_state, urls = {}, []
    for page in pages:
        if page in SEO_SKIP:
            continue
        digest = hashlib.md5(contents[page].encode("utf-8")).hexdigest()
        old = state.get(page, {})
        new_state[page] = {"hash": digest, "date": old["date"] if old.get("hash") == digest else today}
        entry = f"  <url>\n    <loc>{html.escape(page_url(page))}</loc>\n    <lastmod>{new_state[page]['date']}</lastmod>"
        prod = products_by_page.get(page)
        if prod and og_image(prod["image"]):
            entry += (f"\n    <image:image>\n      <image:loc>{html.escape(abs_asset(prod['image']))}</image:loc>"
                      f"\n      <image:title>{html.escape(h1_text(contents[page]))}</image:title>\n    </image:image>")
        urls.append(entry + "\n  </url>")
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(urls) + "\n</urlset>\n")
    write(LASTMOD_FILE, json.dumps(new_state, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"sitemap.xml: {len(urls)} url")


# Catalog-driven products page.
products = json.loads(read("products.json"))
validate_catalog(products)
generate_product_pages(products)
generate_category_pages(products)
try:
    articles = json.loads(read("articles.json"))
except Exception:
    articles = []
generate_article_pages(articles)
articles_by_page = {article_link(a): a for a in articles}
# تا وقتی مقاله‌ای منتشر نشده، articles.html در sitemap قرار نمی‌گیرد (صفحهٔ خالی برای ایندکس مناسب نیست).
if not articles:
    SEO_SKIP_ARTICLES_EMPTY = True
else:
    SEO_SKIP_ARTICLES_EMPTY = False
# URLهای قدیمی محصولات جدید باید noindex شوند و وارد sitemap نشوند.
SEO_SKIP = {"404.html"} | set(REDIRECTS)
if SEO_SKIP_ARTICLES_EMPTY:
    SEO_SKIP.add("articles.html")
write_redirect_pages()

optimize_images()

header = read("partials/header.html").strip()
footer = read("partials/footer.html").strip()
cta = read("partials/cta.html").strip()
no_cta = {"contact.html", "wholesale.html"}
products_by_page = {p["link"]: p for p in products if p.get("link") and p.get("page") is not False}
contents = {}

# ---------------------------------------------------------------------------
# مسیرها: در منبع همهٔ لینک‌های داخلی نسبت به ریشهٔ سایت نوشته می‌شوند (assets/x.css، products.html، ...).
# هنگام نوشتن، برای صفحه‌های داخل زیرپوشه پیشوند «../» اضافه می‌شود (برای 404 مسیر مطلق «/»
# چون سرور آن را روی هر آدرسی نشان می‌دهد). هنگام خواندن، همین پیشوند برداشته می‌شود تا build تکرارپذیر بماند.
# ---------------------------------------------------------------------------
ATTR_RE = re.compile(r'(\b(?:href|src|action)=")([^"]*)(")')
NOT_REL = ("http:", "https:", "//", "/", "#", "tel:", "mailto:", "data:", "javascript:", "sms:")


def to_root_form(s, page):
    if page == "404.html":
        return ATTR_RE.sub(lambda m: m.group(1) + (m.group(2)[1:] if len(m.group(2)) > 1 and m.group(2)[0] == "/" and m.group(2)[1] != "/" else m.group(2)) + m.group(3), s)
    up = "../" * page.count("/")
    if not up:
        return s
    return ATTR_RE.sub(lambda m: m.group(1) + (m.group(2)[len(up):] if m.group(2).startswith(up) else m.group(2)) + m.group(3), s)


def to_page_form(s, page):
    prefix = "/" if page == "404.html" else "../" * page.count("/")
    if not prefix:
        return s
    return ATTR_RE.sub(lambda m: m.group(1) + (m.group(2) if not m.group(2) or m.group(2).startswith(NOT_REL) else prefix + m.group(2)) + m.group(3), s)


all_pages = sorted({f for g in ("*.html", "products/*.html", "categories/*.html", "articles/*.html") for f in pages_in(g)} - set(REDIRECTS))
for page in all_pages:
    s = to_root_form(read(page), page)
    act = active_for(page)
    h = re.sub(r"\{\{active:(\w+)\}\}", lambda m: "active" if m.group(1) == act else "", header)
    h = h.replace('sub-nav-link "', 'sub-nav-link"')
    s = re.sub(r"<!-- @@header:start -->.*?<!-- @@header:end -->",
               lambda m: "<!-- @@header:start -->\n" + h + "\n<!-- @@header:end -->", s, flags=re.S)
    s = re.sub(r"<!-- @@footer:start -->.*?<!-- @@footer:end -->",
               lambda m: "<!-- @@footer:start -->\n" + footer + "\n<!-- @@footer:end -->", s, flags=re.S)
    if page not in no_cta:
        if "<!-- @@cta:start -->" not in s:
            s = s.replace("<!-- @@footer:start -->", "<!-- @@cta:start -->\n<!-- @@cta:end -->\n\n    <!-- @@footer:start -->", 1)
        s = re.sub(r"<!-- @@cta:start -->.*?<!-- @@cta:end -->",
                   lambda m: "<!-- @@cta:start -->\n" + cta + "\n<!-- @@cta:end -->", s, flags=re.S)
    if page == "products.html":
        s = re.sub(r'<span id="pcount">\d+</span> کالا', f'<span id="pcount">{len(products)}</span> کالا', s, count=1)
        if "<!-- @@products:start -->" not in s:
            # Convert the existing hard-coded grid to a generator marker once.
            s = re.sub(r'(<div class="row row-cols-2 row-cols-md-3 g-3 g-md-4">).*?(</div>\n\n</div>\n\n<div id="noResults")',
                       lambda m: m.group(1) + '\n        <!-- @@products:start -->\n        <!-- @@products:end -->\n    ' + m.group(2),
                       s, count=1, flags=re.S)
        s = re.sub(r'<!-- @@products:start -->.*?<!-- @@products:end -->',
                   '<!-- @@products:start -->\n' + render_products(products) + '\n        <!-- @@products:end -->', s, flags=re.S)
        for _cat, _cfg in CATEGORY_LANDINGS.items():
            _slug = _cfg["slug"]
            s = re.sub(rf'href="products\.html\?category={_cat}"', f'href="categories/{_slug}.html"', s)
    if page == "wholesale.html":
        s = re.sub(r"<!-- @@wsmodels:start -->.*?<!-- @@wsmodels:end -->",
                   lambda m: "<!-- @@wsmodels:start -->\n" + render_wholesale_options(products) + "\n<!-- @@wsmodels:end -->",
                   s, flags=re.S)
    s = process_head(s)
    s = process_images(s)
    s = process_icons_a11y(s)
    if page not in SEO_SKIP:
        cfg = SEO_PAGES.get(page, {})
        prod = products_by_page.get(page)
        if cfg.get("title"):
            s = set_title_desc(s, cfg["title"], cfg.get("description", ""))
        elif prod and not prod.get("_generated"):
            t, d, _ = product_meta(prod)          # صفحه‌های قدیمی محصول: عنوان/توضیح از کاتالوگ
            s = set_title_desc(s, t, d)
        s = apply_seo(page, s, prod, products_by_page, products)
    s = to_page_form(s, page)
    contents[page] = s
    write(page, s)
    print("ok", page)

# Restore redirect pages after the generic HTML processing loop so they cannot be overwritten.
write_redirect_pages()

write_robots_and_sitemap(sorted(contents), contents, products_by_page)

# فایل‌های قدیمی dist که دیگر استفاده نمی‌شوند پاک شوند
used = {v.split("?")[0] for v in CSS_BUNDLES.values()}
for f in glob.glob("assets/dist/*.css"):
    if f.replace(os.sep, "/") not in used:
        os.remove(f)
print(f"products: {len(products)} | css bundles: {len(CSS_BUNDLES)}")
