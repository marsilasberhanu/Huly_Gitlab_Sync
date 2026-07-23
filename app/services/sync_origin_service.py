# app/services/sync_origin_service.py


def build_huly_to_gitlab_marker(
    *,
    project_link_id: int,
    huly_issue_id: str,
) -> str:
    """
    Add a hidden marker to GitLab issues created by this sync engine.

    GitLab includes the issue description in its webhook payload.
    The marker lets the webhook recognize its own reflected creation event.
    """
    return (
        f"<!-- huly-gitlab-sync:"
        f"{project_link_id}:"
        f"{huly_issue_id} -->"
    )


def has_huly_to_gitlab_marker(
    *,
    description: str | None,
    project_link_id: int,
) -> bool:
    """
    Return True when a GitLab issue was created by the
    Huly-to-GitLab synchronization for this project link.
    """
    if not description:
        return False

    expected_prefix = (
        f"<!-- huly-gitlab-sync:"
        f"{project_link_id}:"
    )

    return expected_prefix in description
