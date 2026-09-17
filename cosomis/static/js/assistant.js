/* Portal assistant drawer (assistant/).
 *
 * The drawer shell (assistant/_drawer.html) is on every page; this opens and
 * closes it from the navbar toggle, fetches its body once through HTMX on
 * first open, remembers the open state across page loads (localStorage) so a
 * conversation can continue while the user navigates, and wires the chat
 * form: chips, Enter to send, typing indicator, auto-scroll, error toasts.
 */
(function (window, document) {
    "use strict";

    var STORAGE_KEY = "ldp.assistant.open";
    var MAX_INPUT_HEIGHT = 160;

    var drawer = document.getElementById("assistant-drawer");
    if (!drawer) { return; }
    var body = document.body;
    var toggle = document.getElementById("assistant-toggle");
    var closeButton = document.getElementById("assistant-close");
    var backdrop = document.getElementById("assistant-backdrop");
    var panel = document.getElementById("assistant-panel");
    var panelLoaded = false;
    var focusWhenLoaded = false;   // an explicit open wants the input focused once the body arrives

    function remember(open) {
        try { window.localStorage.setItem(STORAGE_KEY, open ? "1" : "0"); } catch (e) { /* private mode */ }
    }
    function remembered() {
        try { return window.localStorage.getItem(STORAGE_KEY) === "1"; } catch (e) { return false; }
    }
    function isOpen() { return body.classList.contains("assistant-open"); }
    function input() { return document.getElementById("assistant-question"); }
    function form() { return document.getElementById("assistant-form"); }
    function log() { return document.getElementById("assistant-log"); }

    function loadPanel() {
        if (panelLoaded || !window.htmx) { return; }
        panelLoaded = true;
        window.htmx.ajax("GET", drawer.getAttribute("data-panel-url"), {
            target: "#assistant-panel", swap: "innerHTML"
        });
    }

    function focusInput() {
        var box = input();
        if (box && !box.disabled && isOpen()) { box.focus(); }
    }

    function scrollToBottom() {
        var el = log();
        if (el) { el.scrollTop = el.scrollHeight; }
    }

    function autosize(box) {
        box.style.height = "auto";
        box.style.height = Math.min(box.scrollHeight, MAX_INPUT_HEIGHT) + "px";
    }

    function open(options) {
        options = options || {};
        body.classList.add("assistant-open");
        drawer.setAttribute("aria-hidden", "false");
        if (toggle) {
            toggle.setAttribute("aria-expanded", "true");
            toggle.classList.remove("has-unread");
        }
        remember(true);
        focusWhenLoaded = !!options.focus;
        loadPanel();
        if (options.focus) { focusInput(); }
    }

    function close() {
        var hadFocus = drawer.contains(document.activeElement);
        body.classList.remove("assistant-open");
        drawer.setAttribute("aria-hidden", "true");
        if (toggle) { toggle.setAttribute("aria-expanded", "false"); }
        remember(false);
        if (hadFocus && toggle) { toggle.focus(); }
    }

    function send() {
        var box = input();
        var f = form();
        if (!box || !f || box.disabled || !box.value.trim() || !window.htmx) { return; }
        window.htmx.trigger(f, "submit");
    }

    if (toggle) {
        toggle.addEventListener("click", function (e) {
            e.preventDefault();
            if (isOpen()) { close(); } else { open({ focus: true }); }
        });
    }
    if (closeButton) { closeButton.addEventListener("click", close); }
    if (backdrop) { backdrop.addEventListener("click", close); }

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isOpen() && drawer.contains(document.activeElement)) { close(); }
    });

    // Everything inside the panel is swapped in by HTMX, so delegate.
    panel.addEventListener("click", function (e) {
        var chip = e.target.closest(".assistant-chip");
        var box = input();
        if (chip && box && !chip.disabled) {
            box.value = chip.getAttribute("data-question") || "";
            autosize(box);
            send();
        }
    });
    panel.addEventListener("keydown", function (e) {
        if (e.target.id !== "assistant-question") { return; }
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
            e.preventDefault();
            send();
        }
    });
    panel.addEventListener("input", function (e) {
        if (e.target.id === "assistant-question") { autosize(e.target); }
    });

    // A redirect (session expired → login page) must not be swapped into the
    // chat log: reload so the user lands on the sign-in page instead.
    drawer.addEventListener("htmx:beforeSwap", function (e) {
        var xhr = e.detail.xhr;
        if (xhr && xhr.responseURL && xhr.responseURL.indexOf("/assistant/") === -1) {
            e.detail.shouldSwap = false;
            window.location.reload();
        }
    });

    drawer.addEventListener("htmx:afterSwap", function (e) {
        var target = e.detail.target;
        if (target === panel) {
            scrollToBottom();
            if (focusWhenLoaded) { focusInput(); }
            focusWhenLoaded = false;
        } else if (target && target.id === "assistant-log") {
            var welcome = document.getElementById("assistant-welcome");
            if (welcome) { welcome.remove(); }
            scrollToBottom();
            if (isOpen()) { focusInput(); } else if (toggle) { toggle.classList.add("has-unread"); }
        }
    });

    drawer.addEventListener("htmx:afterRequest", function (e) {
        if (e.detail.elt !== form()) { return; }
        var box = input();
        if (e.detail.successful && box) {
            box.value = "";
            autosize(box);
        }
    });

    function requestFailed(e) {
        var xhr = e.detail && e.detail.xhr;
        if (typeof window.notifyAjaxError === "function") { window.notifyAjaxError(xhr); }
    }
    drawer.addEventListener("htmx:responseError", requestFailed);
    drawer.addEventListener("htmx:sendError", requestFailed);
    drawer.addEventListener("htmx:timeout", requestFailed);

    // Restore: an explicit link (/assistant/ redirects with ?assistant=open)
    // gets focus; a drawer left open on the previous page reopens silently so
    // it does not steal focus from the page the user just navigated to.
    var params = new window.URLSearchParams(window.location.search);
    if (params.get("assistant") === "open" || window.location.hash === "#assistant") {
        open({ focus: true });
    } else if (remembered()) {
        open({ focus: false });
    }
})(window, document);
