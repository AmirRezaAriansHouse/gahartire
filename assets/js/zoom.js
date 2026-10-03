/* زوم تصویر (لایت‌باکس): کلیک روی عکس محصول و عکس‌های فروشگاه.
   دوبار تپ/کلیک = زوم، چرخ ماوس/پینچ = زوم، کشیدن = جابه‌جایی، Esc/پس‌زمینه = بستن */
(function () {
    'use strict';
    var SEL = '.style-main-img, img[data-zoom]';
    var ov, im, st = { s: 1, x: 0, y: 0 }, pts = {}, startDist = 0, startS = 1, moved = false, list = [], idx = 0, lastTap = 0;

    function apply(anim) {
        im.style.transition = anim ? 'transform .2s ease' : 'none';
        im.style.transform = 'translate(' + st.x + 'px,' + st.y + 'px) scale(' + st.s + ')';
        ov.classList.toggle('is-zoomed', st.s > 1);
    }
    function reset() { st.s = 1; st.x = 0; st.y = 0; }
    function setScale(n, anim) {
        st.s = Math.min(5, Math.max(1, n));
        if (st.s === 1) { st.x = 0; st.y = 0; }
        apply(anim);
    }
    function show(i) {
        idx = (i + list.length) % list.length;
        var el = list[idx];
        im.src = el.currentSrc || el.src;
        im.alt = el.alt || '';
        reset(); apply(false);
        ov.classList.toggle('has-nav', list.length > 1);
    }
    function build() {
        ov = document.createElement('div');
        ov.className = 'gt-zoom';
        ov.setAttribute('role', 'dialog');
        ov.setAttribute('aria-modal', 'true');
        ov.innerHTML = '<button type="button" class="gt-zoom-close" aria-label="بستن">&times;</button>' +
            '<button type="button" class="gt-zoom-nav gt-zoom-prev" aria-label="قبلی">&#8250;</button>' +
            '<button type="button" class="gt-zoom-nav gt-zoom-next" aria-label="بعدی">&#8249;</button>' +
            '<img class="gt-zoom-img" alt="" draggable="false">';
        document.body.appendChild(ov);
        im = ov.querySelector('.gt-zoom-img');
        ov.querySelector('.gt-zoom-close').onclick = close;
        ov.querySelector('.gt-zoom-prev').onclick = function (e) { e.stopPropagation(); show(idx - 1); };
        ov.querySelector('.gt-zoom-next').onclick = function (e) { e.stopPropagation(); show(idx + 1); };
        ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
        im.addEventListener('wheel', function (e) {
            e.preventDefault();
            setScale(st.s * (e.deltaY < 0 ? 1.2 : 1 / 1.2), false);
        }, { passive: false });
        im.addEventListener('dblclick', function () { setScale(st.s > 1 ? 1 : 2.5, true); });
        im.addEventListener('pointerdown', function (e) {
            im.setPointerCapture(e.pointerId);
            pts[e.pointerId] = { x: e.clientX, y: e.clientY };
            moved = false;
            var k = Object.keys(pts);
            if (k.length === 2) { startDist = dist(); startS = st.s; }
        });
        im.addEventListener('pointermove', function (e) {
            var p = pts[e.pointerId]; if (!p) return;
            var k = Object.keys(pts);
            if (k.length === 2) {
                pts[e.pointerId] = { x: e.clientX, y: e.clientY };
                setScale(startS * dist() / startDist, false); moved = true; return;
            }
            var dx = e.clientX - p.x, dy = e.clientY - p.y;
            pts[e.pointerId] = { x: e.clientX, y: e.clientY };
            if (st.s > 1) { st.x += dx; st.y += dy; moved = true; apply(false); }
        });
        function up(e) {
            delete pts[e.pointerId];
            if (!moved && e.pointerType === 'touch' && Object.keys(pts).length === 0) {
                var now = Date.now();
                if (now - lastTap < 300) { setScale(st.s > 1 ? 1 : 2.5, true); lastTap = 0; } else { lastTap = now; }
            }
        }
        im.addEventListener('pointerup', up);
        im.addEventListener('pointercancel', up);
    }
    function dist() {
        var k = Object.keys(pts), a = pts[k[0]], b = pts[k[1]];
        return Math.hypot(a.x - b.x, a.y - b.y) || 1;
    }
    function onKey(e) {
        if (e.key === 'Escape') close();
        else if (list.length > 1 && e.key === 'ArrowLeft') show(idx + 1);
        else if (list.length > 1 && e.key === 'ArrowRight') show(idx - 1);
    }
    function open(el) {
        if (!ov) build();
        var grp = el.closest('.gt-gallery-grid');
        list = grp ? [].slice.call(grp.querySelectorAll('img')) : [el];
        document.documentElement.classList.add('gt-zoom-open');
        ov.classList.add('open');
        show(list.indexOf(el));
        document.addEventListener('keydown', onKey);
        ov.querySelector('.gt-zoom-close').focus();
    }
    function close() {
        if (!ov) return;
        ov.classList.remove('open');
        document.documentElement.classList.remove('gt-zoom-open');
        document.removeEventListener('keydown', onKey);
        pts = {};
    }
    document.addEventListener('click', function (e) {
        var el = e.target.closest && e.target.closest(SEL);
        if (!el || el.closest('a[href]')) return;
        e.preventDefault();
        open(el);
    });
    [].forEach.call(document.querySelectorAll(SEL), function (el) {
        if (!el.closest('a[href]')) { el.style.cursor = 'zoom-in'; }
    });
})();
