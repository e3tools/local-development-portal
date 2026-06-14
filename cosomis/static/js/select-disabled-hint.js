/* Disabled-select hint (UX sprint S10, §5.5 / §2.11).
 *
 * A cascading filter select is disabled until its parent level is chosen, but
 * nothing tells the user *why* it's greyed out. This helper surfaces that reason
 * as a tooltip + accessible label — and only while the select is actually
 * disabled, so an enabled select never carries a stale "choose X first" title.
 *
 * The message is supplied per-select via a `data-disabled-hint` attribute so the
 * string stays in the Django template ({% translate %}) — no user-facing copy
 * lives in this file. select2 renders its own container, so the hint is mirrored
 * there too; otherwise the tooltip would never show on the styled widget.
 *
 * Opt-in: only selects that carry `data-disabled-hint` are touched.
 */
(function (window, document) {
    "use strict";

    function select2Container(select) {
        // select2 inserts its container as the next sibling of the native <select>.
        var next = select.nextElementSibling;
        if (next && next.classList && next.classList.contains("select2")) return next;
        return select.parentNode ? select.parentNode.querySelector(".select2") : null;
    }

    function sync(select) {
        var hint = select.getAttribute("data-disabled-hint");
        if (!hint) return;
        var container = select2Container(select);
        if (select.disabled) {
            select.setAttribute("title", hint);
            select.setAttribute("aria-label", hint);
            if (container) container.setAttribute("title", hint);
        } else {
            select.removeAttribute("title");
            select.removeAttribute("aria-label");
            if (container) container.removeAttribute("title");
        }
    }

    function syncAll() {
        var nodes = document.querySelectorAll("select[data-disabled-hint]");
        Array.prototype.forEach.call(nodes, sync);
    }

    function start() {
        syncAll();
        // Re-run once select2 has had a chance to build its containers.
        window.setTimeout(syncAll, 0);
        if ("MutationObserver" in window) {
            var obs = new MutationObserver(function (mutations) {
                mutations.forEach(function (m) {
                    if (m.target && m.target.tagName === "SELECT" &&
                        m.target.hasAttribute("data-disabled-hint")) {
                        sync(m.target);
                    }
                });
            });
            obs.observe(document.body, {
                subtree: true,
                attributes: true,
                attributeFilter: ["disabled"]
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }

    // Exposed so pages that toggle disabled via libraries can force a refresh.
    window.syncDisabledHints = syncAll;
})(window, document);
