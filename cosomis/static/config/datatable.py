from django.utils.translation import gettext_lazy as _


def get_datatable_config():
    return {
        "language": {
            "sLengthMenu": _("Show _MENU_ registers"),
            "sZeroRecords": _("No result found"),
            "sEmptyTable": _("No result found"),
            "sInfo": _("Showing _START_ to _END_ of _TOTAL_ entries"),
            "sInfoEmpty": _("Showing 0 to 0 of 0 entries"),
            "sSearch": _("Search"),
            "oPaginate": {
                "sFirst": _("First"),
                "sLast": _("Last"),
                "sNext": _("Next"),
                "sPrevious": _("Previous")
            }
        }
    }
