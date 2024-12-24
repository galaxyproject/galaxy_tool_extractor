"""Build URLs for each Lab page for Labs that have been changed in this PR.

Test each URL to see if it returns a 200 status code, and post the results
in a PR comment.
"""

import os
import sys
from github import Github
from pathlib import Path

COMMENT_TITLE_TEMPLATE = "Preview changes to {lab_name} Lab <!--=-->"
URL_TEMPLATE = (
    "https://labs.usegalaxy.org.au"
    "/?content_root=https://github.com/{repo}"
    "/blob/{branch_name}/{lab_content_path}"
    "&cache=false"
)
TRY_FILES = [
    'base.yml',
    'usegalaxy.eu.yml',
    'usegalaxy.org.yml',
    'usegalaxy.org.au.yml',
]

# Environment variables from GitHub Actions
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PR_NUMBER = int(os.environ["PR_NUMBER"])
BASE_REPO = os.getenv("BASE_REPO")


def get_comment(pull_request, id_string):
    """Fetches PR comments and scans for the COMMENT_TITLE_TEMPLATE."""
    for comment in pull_request.get_issue_comments():
        if id_string in comment.body:
            return comment
    return None


def create_or_update_comment(lab_name, body_md):
    """Creates or updates a comment for the given lab name.

    Checks for an existing comment by looking for the COMMENT_TITLE_TEMPLATE
    in existing comments.
    """
    divider = "\n\n" + '-' * 80 + '\n\n'
    print("Posting comment:", divider, body_md.strip(' \n'), divider)
    title_string = COMMENT_TITLE_TEMPLATE.format(lab_name=lab_name)
    gh = Github(GITHUB_TOKEN)
    print("Getting base repo:", BASE_REPO)
    repo = gh.get_repo(BASE_REPO)
    pull_request = repo.get_pull(PR_NUMBER)
    comment = get_comment(pull_request, title_string)
    if comment:
        comment.edit(body_md)
    else:
        pull_request.create_issue_comment(body_md)


def main():
    comments_dir = Path(sys.argv[1] if len(sys.argv) else "comments")
    if (
        comments_dir.exists()
        and comments_dir.is_dir()
        and list(comments_dir.glob('*.md'))
    ):
        for path in comments_dir.glob('*.md'):
            with open(path) as f:
                comment_md = f.read()
            lab_name = path.stem
            print(f"Posting PR comment for {lab_name}...")
            create_or_update_comment(lab_name, comment_md)
    else:
        print("No comments to post - exiting")


if __name__ == "__main__":
    main()
