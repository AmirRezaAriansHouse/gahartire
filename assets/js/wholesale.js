/* فرم فروش عمده چندمدلی: لیست مدل‌ها + تعداد را به‌صورت یک پیام واتساپ آماده می‌کند */
(function () {
    var form = document.getElementById('wsForm');
    var rowsEl = document.getElementById('wsRows');
    var tpl = document.getElementById('wsRowTpl');
    if (!form || !rowsEl || !tpl) return;

    var addBtn = document.getElementById('wsAdd');
    var copyBtn = document.getElementById('wsCopy');
    var summary = document.getElementById('wsSummary');
    var status = document.getElementById('wsStatus');
    var MAX_ROWS = 20, CUSTOM = '__custom';
    var WA = 'https://wa.me/989120346053?text=';

    var fa = function (n) { return String(n).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'.charAt(d); }); };
    var say = function (t) { if (status) status.textContent = t; };
    var val = function (id) { var el = document.getElementById(id); return el ? (el.value || '').trim() : ''; };
    var q = function (row, sel) { return row.querySelector(sel); };
    var rows = function () { return Array.prototype.slice.call(rowsEl.querySelectorAll('[data-ws-row]')); };

    function qtyOf(row) {
        var n = parseInt(q(row, '.ws-qty-input').value, 10);
        return isFinite(n) ? n : 0;
    }

    function labelOf(row) {
        var sel = q(row, '.ws-model');
        if (sel.value === CUSTOM) return q(row, '.ws-custom').value.trim();
        if (!sel.value) return '';
        return sel.options[sel.selectedIndex].text.trim();
    }

    function isBlank(row) { return !q(row, '.ws-model').value && !q(row, '.ws-qty-input').value.trim(); }
    function isValid(row) { return !!labelOf(row) && qtyOf(row) >= 1; }

    function updateSummary() {
        var ok = rows().filter(isValid);
        var total = ok.reduce(function (a, r) { return a + qtyOf(r); }, 0);
        summary.textContent = ok.length
            ? fa(ok.length) + ' مدل · جمعاً ' + fa(total) + ' حلقه'
            : 'هنوز مدلی ثبت نشده است';
        if (addBtn) addBtn.disabled = rows().length >= MAX_ROWS;
    }

    function addRow(modelValue, focus) {
        if (rows().length >= MAX_ROWS) { say('حداکثر ' + fa(MAX_ROWS) + ' مدل در هر سفارش قابل ثبت است؛ برای بیشتر تماس بگیرید.'); return null; }
        var row = tpl.content.firstElementChild.cloneNode(true);
        var sel = q(row, '.ws-model'), custom = q(row, '.ws-custom'), qty = q(row, '.ws-qty-input');
        if (modelValue) sel.value = modelValue;
        if (sel.value !== modelValue) sel.value = '';

        sel.addEventListener('change', function () {
            var isCustom = sel.value === CUSTOM;
            custom.classList.toggle('d-none', !isCustom);
            if (isCustom) custom.focus();
            sel.classList.remove('is-invalid'); updateSummary();
        });
        custom.addEventListener('input', function () { custom.classList.remove('is-invalid'); updateSummary(); });
        qty.addEventListener('input', function () { qty.classList.remove('is-invalid'); updateSummary(); });
        row.addEventListener('click', function (e) {
            var b = e.target.closest('.ws-qbtn');
            if (b) {
                var n = Math.max(0, qtyOf(row) + parseInt(b.getAttribute('data-d'), 10));
                qty.value = n >= 1 ? n : '';
                qty.classList.remove('is-invalid'); updateSummary();
            } else if (e.target.closest('.ws-remove')) {
                if (rows().length > 1) { row.remove(); }
                else { sel.value = ''; custom.value = ''; custom.classList.add('d-none'); qty.value = ''; }
                updateSummary();
            }
        });
        rowsEl.appendChild(row);
        updateSummary();
        if (focus) sel.focus();
        return row;
    }

    // اعتبارسنجی؛ ردیف‌های کاملاً خالی نادیده گرفته می‌شوند
    function collect() {
        var all = rows(), active = all.filter(function (r) { return !isBlank(r); }), firstBad = null;
        all.forEach(function (r) {
            ['.ws-model', '.ws-custom', '.ws-qty-input'].forEach(function (s) { q(r, s).classList.remove('is-invalid'); });
        });
        active.forEach(function (r) {
            var sel = q(r, '.ws-model'), custom = q(r, '.ws-custom'), qty = q(r, '.ws-qty-input'), bad = null;
            if (!sel.value) bad = sel;
            else if (sel.value === CUSTOM && !custom.value.trim()) bad = custom;
            if (bad) { bad.classList.add('is-invalid'); firstBad = firstBad || bad; }
            if (qtyOf(r) < 1) { qty.classList.add('is-invalid'); firstBad = firstBad || qty; }
        });
        if (!active.length) { var s0 = q(all[0], '.ws-model'); s0.classList.add('is-invalid'); firstBad = s0; }
        return { items: active.filter(isValid), bad: firstBad, hasActive: active.length > 0 };
    }

    function buildMessage(items) {
        var total = items.reduce(function (a, r) { return a + qtyOf(r); }, 0);
        var lines = ['سلام، برای خرید عمده لاستیک استعلام قیمت و موجودی دارم.'];
        if (val('wsName')) lines.push('نام: ' + val('wsName'));
        if (val('wsType')) lines.push('نوع مشتری: ' + val('wsType'));
        if (val('wsCity')) lines.push('شهر مقصد: ' + val('wsCity'));
        lines.push('', 'لیست مدل‌ها:');
        items.forEach(function (r, i) { lines.push(fa(i + 1) + ') ' + labelOf(r) + ' — ' + fa(qtyOf(r)) + ' حلقه'); });
        lines.push('جمع: ' + fa(items.length) + ' مدل، ' + fa(total) + ' حلقه');
        if (val('wsNote')) lines.push('', 'توضیحات: ' + val('wsNote'));
        return lines.join('\n');
    }

    function validated() {
        var r = collect();
        if (r.bad || !r.items.length) {
            say(r.hasActive ? 'برای هر ردیف، مدل و تعداد (حداقل ۱) را کامل کنید.' : 'حداقل یک مدل و تعداد آن را وارد کنید.');
            if (r.bad) r.bad.focus();
            return null;
        }
        return r.items;
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var items = validated(); if (!items) return;
        say('لیست آماده شد؛ واتساپ باز می‌شود.');
        window.open(WA + encodeURIComponent(buildMessage(items)), '_blank', 'noopener');
    });

    if (copyBtn) copyBtn.addEventListener('click', function () {
        var items = validated(); if (!items) return;
        var text = buildMessage(items);
        var done = function () { say('لیست کپی شد.'); copyBtn.lastChild.textContent = ' کپی شد ✓'; setTimeout(function () { copyBtn.lastChild.textContent = ' کپی لیست'; }, 2000); };
        if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done, function () { say('کپی انجام نشد.'); }); return; }
        var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy') ? done() : say('کپی انجام نشد.'); } catch (_) { say('کپی انجام نشد.'); }
        document.body.removeChild(ta);
    });

    if (addBtn) addBtn.addEventListener('click', function () { addRow('', true); });

    // پیش‌انتخاب از لینک «خرید عمده این مدل» (?model=slug یا چند مدل با ویرگول)
    var added = 0, m = /[?&]model=([^&#]*)/.exec(location.search);
    if (m) decodeURIComponent(m[1]).split(',').forEach(function (slug) {
        slug = slug.trim();
        if (slug && added < MAX_ROWS) { var r = addRow(slug); if (r && q(r, '.ws-model').value) added++; else if (r) r.remove(); }
    });
    if (!rows().length) addRow('');
})();
