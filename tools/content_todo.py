#!/usr/bin/env python3
"""
گزارش محصولاتی که هنوز اطلاعات واقعی (caption/fits/features) ندارند:   python3 tools/content_todo.py
خروجی: CONTENT-TODO.md؛ محصولات هم‌سایز (که بیشترین ریسک محتوای تکراری را دارند) اول می‌آیند.
فقط اطلاعاتی را وارد کنید که مطمئنید درست است (خودروهای سازگار، ضمانت، تاریخ تولید، تفاوت برندها).
"""
import collections, json, os
from pathlib import Path
os.chdir(Path(__file__).resolve().parent.parent)
P = [p for p in json.loads(Path("products.json").read_text(encoding="utf-8")) if p.get("page") is not False]

def norm(s): return (s or "").strip().upper().replace(" ", "")
groups = collections.defaultdict(list)
for p in P: groups[norm(p.get("size"))].append(p)

def missing(p):
    return [k for k in ("fits", "features") if not p.get(k)] + ([] if (p.get("caption") or "").strip() else ["caption"])

lines = ["# محتوای واقعی که باید برای محصولات بنویسید", "",
         "هر مورد را در `products.json` به همان محصول اضافه کنید (فیلدهای `caption`، `fits`، `features`) و `python3 build.py` بزنید.",
         "گروه‌های هم‌سایز اول آمده‌اند؛ تفاوت واقعی برندها (کیفیت، کاربرد، ضمانت، تاریخ تولید) همان چیزی است که صفحه‌ها را از هم جدا می‌کند.", ""]
for size, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    todo = [p for p in items if missing(p)]
    if not todo: continue
    tag = f"{len(items)} برند هم‌سایز" if len(items) > 1 else "تک‌برند"
    lines += [f"## {items[0].get('size')} — {tag}", ""]
    for p in todo:
        lines.append(f"- **{p['id']}** ({p.get('vehicle') or '—'} / {p.get('brand')}) — کم‌دارد: {'، '.join(missing(p))}")
    lines += ["", "```json", json.dumps({"id": todo[0]["id"], "caption": "", "fits": [""], "features": [""]}, ensure_ascii=False, indent=2), "```", ""]
Path("CONTENT-TODO.md").write_text("\n".join(lines), encoding="utf-8")
print(f"{sum(1 for p in P if missing(p))} از {len(P)} محصول اطلاعات ناقص دارند ← CONTENT-TODO.md")
