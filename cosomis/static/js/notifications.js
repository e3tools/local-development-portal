/* Accessible toast / error layer — UX sprint S7.
 *
 * Single mechanism for transient feedback. Supersedes:
 *   - the old colour-only pushNotify() (kept as a backward-compatible shim),
 *   - the modal path for non-danger Django messages (see common/messages.html),
 *   - raw `alert(error_server_message + status)` calls in AJAX error handlers.
 *
 * Colours come from the brand tokens in custom.css (--color-success/info/warning/danger)
 * so toasts stay on-brand. User-facing strings are sourced from window.APP_I18N
 * (set via {% translate %} in foot.html); English fallbacks keep this robust on
 * pages that don't define it.
 */
(function (window, document) {
    "use strict";

    var CONTAINER_ID = "push-notification-container";

    // type -> brand colour token + accessibility semantics.
    // danger/warning interrupt (assertive + role=alert); success/info are polite.
    var TYPES = {
        success: { token: "--color-success", live: "polite", role: "status" },
        info: { token: "--color-info", live: "polite", role: "status" },
        warning: { token: "--color-warning", live: "assertive", role: "alert" },
        danger: { token: "--color-danger", live: "assertive", role: "alert" }
    };

    // Map the tag vocabulary used across the app/Django messages onto our four types.
    var ALIASES = {
        error: "danger",
        danger: "danger",
        success: "success",
        info: "info",
        warning: "warning",
        secondary: "info",
        primary: "info",
        debug: "info"
    };

    function i18n(key, fallback) {
        return (window.APP_I18N && window.APP_I18N[key]) || fallback;
    }

    function normalizeType(type) {
        if (!type) return "info";
        return ALIASES[type] || (TYPES[type] ? type : "info");
    }

    function container() {
        var el = document.getElementById(CONTAINER_ID);
        if (!el) {
            el = document.createElement("div");
            el.id = CONTAINER_ID;
            document.body.appendChild(el);
        }
        // Ensure live-region semantics even if the markup predates S7.
        el.setAttribute("role", "region");
        if (!el.getAttribute("aria-label")) {
            el.setAttribute("aria-label", i18n("notifications", "Notifications"));
        }
        el.setAttribute("aria-live", "polite");
        return el;
    }

    /**
     * Show a toast.
     * @param {string} message  Message HTML (already-escaped server strings are fine).
     * @param {string} [type]   success | info | warning | danger (alias: error).
     * @param {object} [opts]   { timeout } ms before auto-dismiss; 0 = sticky.
     * @returns {HTMLElement|null}
     */
    function toast(message, type, opts) {
        if (!message) return null;
        type = normalizeType(type);
        opts = opts || {};
        var conf = TYPES[type];
        var timeout = typeof opts.timeout === "number"
            ? opts.timeout
            : (type === "success" ? 5000 : 10000);

        var el = document.createElement("div");
        el.className = "app-toast app-toast--" + type;
        el.setAttribute("role", conf.role);
        el.setAttribute("aria-live", conf.live);

        var body = document.createElement("span");
        body.className = "app-toast__body";
        body.innerHTML = message;

        var close = document.createElement("button");
        close.type = "button";
        close.className = "app-toast__close";
        close.setAttribute("aria-label", i18n("close", "Close"));
        close.innerHTML = "&times;";
        close.addEventListener("click", function () { dismiss(el); });

        el.appendChild(body);
        el.appendChild(close);
        container().appendChild(el);

        // Enter animation on the next frame so the transition runs.
        window.requestAnimationFrame(function () { el.classList.add("app-toast--in"); });

        if (timeout > 0) {
            el._timer = window.setTimeout(function () { dismiss(el); }, timeout);
        }
        return el;
    }

    function dismiss(el) {
        if (!el) return;
        if (el._timer) window.clearTimeout(el._timer);
        el.classList.remove("app-toast--in");
        el.classList.add("app-toast--out");
        window.setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 400);
    }

    /**
     * Turn a failed jqXHR (or fetch-like error) into a human message that
     * distinguishes network / session-expired / validation / server error,
     * instead of leaking "Error 500" to the user.
     */
    function ajaxErrorMessage(xhr) {
        var status = xhr && (xhr.status != null ? xhr.status : xhr.statusCode);
        if (!status) {
            return i18n("errNetwork", "Network error — please check your connection and try again.");
        }
        if (status === 401 || status === 403) {
            return i18n("errSession", "Your session has expired. Please reload the page and sign in again.");
        }
        if (status === 400 || status === 422) {
            return i18n("errValidation", "Some information is invalid. Please review the form and try again.");
        }
        if (status >= 500) {
            return i18n("errServer", "The server ran into a problem. Please try again in a moment.");
        }
        return i18n("errGeneric", "Something went wrong.") + " (" + status + ")";
    }

    /** Show an AJAX failure as a danger toast with a category-aware message. */
    function notifyAjaxError(xhr, type) {
        return toast(ajaxErrorMessage(xhr), type || "danger");
    }

    /**
     * Render server-side Django messages (emitted as hidden .js-server-toast nodes
     * by common/messages.html) as toasts. Works for both full-page loads and the
     * AJAX-injected path (showPopupMessage in grm.js calls this).
     */
    function renderServerToasts(root) {
        var scope = root || document;
        var nodes = scope.querySelectorAll(".js-server-toast");
        Array.prototype.forEach.call(nodes, function (node) {
            toast(node.innerHTML, node.getAttribute("data-toast-type"));
            if (node.parentNode) node.parentNode.removeChild(node);
        });
    }

    /** Backward-compatible shim: pushNotify(message, type, timeout). */
    function pushNotify(message, type, timeout) {
        return toast(message, normalizeType(type), { timeout: timeout });
    }

    window.toast = toast;
    window.dismissToast = dismiss;
    window.ajaxErrorMessage = ajaxErrorMessage;
    window.notifyAjaxError = notifyAjaxError;
    window.renderServerToasts = renderServerToasts;
    window.pushNotify = pushNotify;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { renderServerToasts(); });
    } else {
        renderServerToasts();
    }
})(window, document);
