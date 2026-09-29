/*!
 * Disable submit buttons and show a spinner while a form is submitting.
 *
 * Markup contract (per submit button):
 *   <button type="submit" data-loading-text="…">
 *     <span class="submit-spin spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
 *     <span class="submit-label">Log in</span>
 *   </button>
 *
 * The spinner is hidden on load and revealed on submit. If the button declares
 * a data-loading-text, the .submit-label text is swapped to it so the user sees
 * the action is in progress.
 */

function disableOnSubmit(selector) {
    selector.find(":submit").each(function () {
        var $btn = $(this);
        $btn.attr("disabled", "disabled").attr("aria-busy", "true");
        var loadingText = $btn.data("loading-text");
        var $label = $btn.find(".submit-label");
        if (loadingText && $label.length) {
            $label.text(loadingText);
        }
    });
    selector.find(".disabled-on-submit").addClass("disabled");
    selector.find(".submit-spin").show();
}

$(function () {
    $(".submit-spin").hide();

    $("form").on("submit", function () {
        // Native HTML5 constraint validation suppresses the submit event when
        // the form is invalid, so reaching here means it is really being sent.
        // Guard explicitly in case a browser still fires it.
        if (this.checkValidity && !this.checkValidity()) {
            return;
        }
        disableOnSubmit($(this));
    });

    $(".disabled-on-submit").on("click", function () {
        disableOnSubmit($("form"));
    });
});
