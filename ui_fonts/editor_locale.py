"""Rendering language for browser note fields; never touches saved field HTML."""

import json


def editor_locale_script(locale: str) -> str:
    payload = json.dumps(locale, ensure_ascii=True).replace("<", "\\u003c")
    return """(() => {
const locale = PAYLOAD;
const key = '__ankiUiFontsEditorLocale';
const selector = '.editing-area';
let state = window[key];
if (!locale) {
    if (!state) return;
    state.observer.disconnect();
    document.querySelectorAll(selector).forEach(element => {
        if (!state.original.has(element)) return;
        const original = state.original.get(element);
        if (original === null) element.removeAttribute('lang');
        else element.setAttribute('lang', original);
    });
    delete window[key];
    return;
}
if (!state) {
    state = { locale, original: new WeakMap() };
    state.apply = () => {
        document.querySelectorAll(selector).forEach(element => {
            if (!state.original.has(element))
                state.original.set(element, element.getAttribute('lang'));
            if (element.getAttribute('lang') !== state.locale)
                element.setAttribute('lang', state.locale);
        });
    };
    // Watch only for newly mounted field wrappers. Text/formatting changes
    // inside the editable are ignored, and shadow roots are not traversed.
    state.observer = new MutationObserver(records => {
        if (records.some(record => Array.from(record.addedNodes).some(node =>
            node.nodeType === 1 && (node.matches(selector) || node.querySelector(selector))
        ))) state.apply();
    });
    window[key] = state;
    const start = () => {
        if (window[key] !== state) return;
        state.apply();
        state.observer.observe(document.body, {childList: true, subtree: true});
    };
    if (document.body) start();
    else document.addEventListener('DOMContentLoaded', start, {once: true});
}
state.locale = locale;
state.apply();
})();""".replace("PAYLOAD", payload)
