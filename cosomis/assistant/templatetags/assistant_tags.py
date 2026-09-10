import html

import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="assistant_markdown")
def assistant_markdown(text):
    """Render the model's Markdown; raw HTML in it is escaped, not trusted."""
    rendered = markdown.markdown(
        html.escape(text or ""), extensions=["tables", "nl2br", "sane_lists"],
    )
    return mark_safe(rendered)  # noqa: S308 — input was escaped above
