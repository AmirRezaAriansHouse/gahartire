import re, glob, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://gahartirekh.ir"
files = glob.glob("**/*.html", recursive=True) + ["sitemap.xml"]
files = [f for f in files if not f.startswith(("templates/", "partials/", "tools/", "node_modules/"))]
n = 0
for f in files:
    if not os.path.exists(f): continue
    s = open(f, encoding="utf-8").read(); o = s
    # لینک کامل به خود سایت
    s = s.replace(f"{SITE}/index.html", f"{SITE}/")
    s = re.sub(re.escape(SITE) + r'/([^"\'<>\s#?]*?)\.html', rf"{SITE}/\1", s)
    # لینک‌های نسبی داخل href
    s = re.sub(r'href="((?:\.\./)*)index\.html"', lambda m: 'href="%s"' % (m.group(1) or "/"), s)
    s = re.sub(r'href="((?![a-z]+:|//)[^"#?]*?)\.html([#?][^"]*)?"', lambda m: 'href="%s%s"' % (m.group(1), m.group(2) or ""), s)
    s = re.sub(r'action="((?![a-z]+:|//)[^"#?]*?)\.html"', r'action="\1"', s)
    if s != o:
        open(f, "w", encoding="utf-8").write(s); n += 1
print("updated files:", n)
