// Optional analytics: no vendor code or identifiers before the device's choice.
(() => {
    const PRODUCT = 'OpenWorld', KEY = 'openworld.analytics.v1';
    const PATHS = new Set(['/', '/privacy']);
    const EVENTS = new Set(["chat_message_sent", "chat_response", "version_created", "example_prompt_clicked", "version_shared", "version_suggested", "version_published", "user_login", "user_signup", "store_random_clicked", "store_opened", "version_starred", "version_unstarred", "store_play_clicked"]);
    const config = window.SiteAnalyticsConfig || {};
    const ga = /^G-[A-Z0-9]+$/.test(config.gaId || '') ? config.gaId : '';
    const token = /^[a-f0-9]{32}$/i.test(config.mixpanelToken || '') ? config.mixpanelToken : '';
    const betterloop = /^bl_[a-z0-9_-]{8,200}$/i.test(config.betterloopKey || '') ? config.betterloopKey : '';
    const ID_KEY = KEY + '.device';
    let allowed = false, active = false, choiceFailed = false, pageSent = '', device = '', trigger = null;
    let googleStarted = false, betterloopReady = false, betterloopLoading = false, dialog;
    const privacySignal = () => navigator.doNotTrack === '1' || window.doNotTrack === '1' || navigator.globalPrivacyControl === true;
    const path = () => { const value = location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/'; return value === '/index' ? '/' : value; };
    const read = () => { try { return localStorage.getItem(KEY) === 'allowed'; } catch { return false; } };
    const permitted = () => !choiceFailed && allowed && read() && !privacySignal() && PATHS.has(path());
    const safePage = () => ({ page_location: location.origin + path(), page_referrer: '', page_title: PRODUCT });
    const status = message => { if (dialog) dialog.querySelector('[data-analytics-status]').textContent = message; };
    function clearIdentifiers() {
        device = '';
        try { localStorage.removeItem(ID_KEY); } catch { /* Off does not need storage. */ }
        try { sessionStorage.removeItem('_fp_sid'); } catch { /* May be blocked. */ }
        const domains = ['', location.hostname, '.' + location.hostname], parts = location.hostname.split('.');
        if (parts.length > 2) domains.push('.' + parts.slice(-2).join('.'));
        for (const cookie of document.cookie.split(';')) {
            const name = cookie.trim().split('=')[0];
            if (/^(_ga(?:_|$)|mp_)/.test(name)) for (const domain of domains) document.cookie = name + '=; Max-Age=0; Path=/; SameSite=Lax' + (domain ? '; Domain=' + domain : '');
        }
    }
    function stop() {
        active = false; pageSent = '';
        if (ga) window['ga-disable-' + ga] = true;
        window.Betterloop?.shutdown?.({ discard: true });
        if (window.dataLayer) window.dataLayer.length = 0;
        clearIdentifiers();
    }
    function mixpanel(event) {
        if (!token || !device || !permitted()) return;
        const data = { event, properties: { token, distinct_id: device, product: PRODUCT, path: path(), $insert_id: crypto.randomUUID(), time: Math.floor(Date.now() / 1000) } };
        void fetch('https://api.mixpanel.com/track?ip=0', { method: 'POST', credentials: 'omit', referrerPolicy: 'no-referrer',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ data: JSON.stringify(data), ip: '0' }).toString(),
        }).catch(() => { /* Optional analytics cannot interrupt the product. */ });
    }
    function startBetterloop() {
        if (!betterloop || !permitted()) return;
        if (betterloopReady && window.Betterloop) {
            window.Betterloop.init({ key: betterloop, endpoint: 'https://betterloopai.com/api/ingest', captureText: false,
                includePaths: [...PATHS].flatMap(value => value === '/' ? ['/', '/index', '/index.html'] : [value, value + '.html']),
                excludePaths: ['/contact', '/account', '/admin', '/owner', '/owner.html', '/auth', '/login', '/signup', '/reset', '/v', '/game', '/shared'],
                excludeSelectors: ['form', '[role="dialog"]', '[data-private]', '[data-betterloop-ignore]'] });
        } else if (!betterloopLoading) {
            betterloopLoading = true;
            const script = document.createElement('script'); script.async = true;
            // No data-key: loading must not auto-initialize after withdrawal.
            script.src = 'https://betterloopai.com/sdk.js?v=20261030'; script.referrerPolicy = 'no-referrer';
            script.onload = () => { betterloopReady = true; betterloopLoading = false; if (permitted()) startBetterloop(); };
            script.onerror = () => { betterloopLoading = false; };
            document.head.appendChild(script);
        }
    }
    function startGoogle() {
        if (!ga || !permitted()) return;
        window['ga-disable-' + ga] = false;
        window.dataLayer = window.dataLayer || [];
        window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
        window.gtag('consent', googleStarted ? 'update' : 'default', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
        window.gtag('js', new Date());
        window.gtag('config', ga, { send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false, ...safePage() });
        if (!googleStarted) {
            googleStarted = true;
            const script = document.createElement('script'); script.async = true; script.referrerPolicy = 'no-referrer';
            script.src = 'https://www.googletagmanager.com/gtag/js?id=' + ga;
            document.head.appendChild(script);
        }
    }
    function apply(value) {
        allowed = value;
        const ready = permitted();
        document.querySelectorAll('[data-analytics-summary]').forEach(el => {
            el.textContent = privacySignal() ? 'Optional analytics is off because this browser requests privacy.' : choiceFailed ? 'Optional analytics is off because your choice could not be saved.' : !allowed ? 'Optional website analytics is off.' :
                !PATHS.has(path()) ? 'Analytics is allowed on this device, but never runs on this private or contact page.' : 'Optional website analytics is allowed on this device.';
        });
        if (!ready) { stop(); return; }
        if (token && !device) {
            try { const saved = localStorage.getItem(ID_KEY); device = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(saved || '') ? saved : crypto.randomUUID(); localStorage.setItem(ID_KEY, device); if (localStorage.getItem(ID_KEY) !== device) throw Error('Storage unavailable'); }
            catch { stop(); status('This browser could not save the choice. Analytics remains off.'); return; }
        }
        active = true; startGoogle(); startBetterloop();
        if (pageSent !== path()) { pageSent = path(); if (ga) window.gtag('event', 'page_view', safePage()); mixpanel('page_view'); }
    }
    const analytics = { track(event) {
        if (!active || !permitted() || !EVENTS.has(event)) return;
        if (ga && window.gtag) window.gtag('event', event, safePage());
        mixpanel(event); if (betterloopReady) window.Betterloop?.track?.(event);
    } };
    window.SiteAnalytics = analytics;
    if (ga) window['ga-disable-' + ga] = true;
    function init() {
        dialog = document.getElementById('analytics-dialog');
        const save = value => {
            try { localStorage.setItem(KEY, value ? 'allowed' : 'off'); if (localStorage.getItem(KEY) !== (value ? 'allowed' : 'off')) throw Error('Storage unavailable'); choiceFailed = false; }
            catch { choiceFailed = true; allowed = false; stop(); status('This browser could not save the choice. Analytics remains off.'); return; }
            status(''); apply(value); dialog.close();
        };
        document.querySelectorAll('[data-analytics-open]').forEach(button => button.addEventListener('click', () => { trigger = button; dialog.showModal(); dialog.querySelector('[data-analytics-off]').focus(); }));
        dialog.querySelector('[data-analytics-off]').addEventListener('click', () => save(false));
        dialog.querySelector('[data-analytics-allow]').addEventListener('click', () => save(true));
        dialog.querySelector('[data-analytics-close]').addEventListener('click', () => dialog.close());
        dialog.addEventListener('close', () => { if (trigger?.isConnected) trigger.focus({ preventScroll: true }); });
        dialog.addEventListener('keydown', event => {
            event.stopPropagation();
            if (event.key !== 'Tab') return;
            const controls = [...dialog.querySelectorAll('button,a[href]')];
            if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1).focus(); }
            if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0].focus(); }
        });
        apply(read());
    }
    document.addEventListener('DOMContentLoaded', init);
    window.addEventListener('storage', event => { if (event.key === KEY) apply(read()); });
    window.addEventListener('pageshow', () => apply(read()));
    window.addEventListener('focus', () => apply(read()));
})();
