from markupsafe import Markup
from sqladmin import ModelView

from app.db.models import ClinicalTrial, TrialStatus


class ClinicalTrialAdmin(ModelView, model=ClinicalTrial):
    column_list = [
        ClinicalTrial.nct_id,
        ClinicalTrial.brief_title,
        ClinicalTrial.status,
        ClinicalTrial.last_update_post_date,
    ]

    # Read-only fields in the form
    form_widget_args = {
        "nct_id": {"readonly": True},
        "brief_title": {"readonly": True},
        "brief_summary": {"readonly": True},
    }

    # Allow editing only specific fields (though read-only widget args above handle UI,
    # logic below enforces)
    # SQLAdmin doesn't have a strict "edit_columns" vs "create_columns" in the same way,
    # but excluding them from form might remove them.
    # A safer way to ensure they are present but readonly is form_widget_args.
    # We want admin to edit custom_summary and status.

    form_columns = ["nct_id", "brief_title", "brief_summary", "custom_brief_summary", "status"]

    # Column formatting for status
    @staticmethod
    def status_formatter(view, context, model, name):
        status = getattr(model, name)
        color = "gray"
        if status == TrialStatus.APPROVED:
            color = "green"
        elif status == TrialStatus.REJECTED:
            color = "red"
        elif status == TrialStatus.PENDING_REVIEW:
            color = "orange"

        return Markup(
            f'<span style="color: {color}; font-weight: bold;">{status.value}</span>'
        )

    column_formatters = {ClinicalTrial.status: status_formatter} # type: ignore
