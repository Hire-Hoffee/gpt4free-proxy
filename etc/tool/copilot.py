import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import g4f
import json
import os
import re
import requests
from typing import Union
from github import Github
from github.PullRequest import PullRequest

g4f.debug.logging = True
g4f.debug.version_check = False

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY')
G4F_PROVIDER = os.getenv('G4F_PROVIDER')
G4F_MODEL = os.getenv('G4F_MODEL') or g4f.models.default

def get_pr_details(github: Github) -> PullRequest:
    """
    Retrieves the details of the pull request from GitHub.

    Args:
        github (Github): The Github object to interact with the GitHub API.

    Returns:
        PullRequest: An object representing the pull request.
    """
    with open('./pr_number', 'r') as file:
        pr_number = file.read().strip()
    if not pr_number:
        return

    repo = github.get_repo(GITHUB_REPOSITORY)
    pull = repo.get_pull(int(pr_number))

    return pull

def get_diff(diff_url: str) -> str:
    """
    Fetches the diff of the pull request from a given URL.

    Args:
        diff_url (str): URL to the pull request diff.

    Returns:
        str: The diff of the pull request.
    """
    response = requests.get(diff_url)
    response.raise_for_status()
    return response.text

def read_json(text: str) -> dict:
    """
    Parses JSON code block from a string.

    Args:
        text (str): A string containing a JSON code block.

    Returns:
        dict: A dictionary parsed from the JSON code block.
    """
    match = re.search(r"```(json|)\n(?P<code>[\S\s]+?)\n```", text)
    if match:
        text = match.group("code")
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        print("No valid json:", text)
        return {}

def read_text(text: str) -> str:
    """
    Extracts text from a markdown code block.

    Args:
        text (str): A string containing a markdown code block.

    Returns:
        str: The extracted text.
    """
    match = re.search(r"```(markdown|)\n(?P<text>[\S\s]+?)\n```", text)
    if match:
        return match.group("text")
    return text

def get_ai_response(prompt: str, as_json: bool = True) -> Union[dict, str]:
    """
    Gets a response from g4f API based on the prompt.

    Args:
        prompt (str): The prompt to send to g4f.
        as_json (bool): Whether to parse the response as JSON.

    Returns:
        Union[dict, str]: The parsed response from g4f, either as a dictionary or a string.
    """
    response = g4f.ChatCompletion.create(
        G4F_MODEL,
        [{'role': 'user', 'content': prompt}],
        G4F_PROVIDER,
        ignore_stream_and_auth=True
    )
    return read_json(response) if as_json else read_text(response)

def analyze_code(pull: PullRequest, diff: str)-> list[dict]:
    """
    Analyzes the code changes in the pull request.

    Args:
        pull (PullRequest): The pull request object.
        diff (str): The diff of the pull request.

    Returns:
        list[dict]: A list of comments generated by the analysis.
    """
    comments = []
    changed_lines = []
    current_file_path = None
    offset_line = 0

    for line in diff.split('\n'):
        if line.startswith('+++ b/'):
            current_file_path = line[6:]
            changed_lines = []
        elif line.startswith('@@'):
            match = re.search(r'\+([0-9]+?),', line)
            if match:
                offset_line = int(match.group(1))
        elif current_file_path:
            if (line.startswith('\\') or line.startswith('diff')) and changed_lines:
                prompt = create_analyze_prompt(changed_lines, pull, current_file_path)
                response = get_ai_response(prompt)
                for review in response.get('reviews', []):
                    review['path'] = current_file_path
                    comments.append(review)
                current_file_path = None
            elif line.startswith('-'):
                changed_lines.append(line)
            else:
                changed_lines.append(f"{offset_line}:{line}")
                offset_line += 1

    return comments

def create_analyze_prompt(changed_lines: list[str], pull: PullRequest, file_path: str):
    """
    Creates a prompt for the g4f model.

    Args:
        changed_lines (list[str]): The lines of code that have changed.
        pull (PullRequest): The pull request object.
        file_path (str): The path to the file being reviewed.

    Returns:
        str: The generated prompt.
    """
    code = "\n".join(changed_lines)
    example = '{"reviews": [{"line": <line_number>, "body": "<review comment>"}]}'
    return f"""Your task is to review pull requests. Instructions:
- Provide the response in following JSON format: {example}
- Do not give positive comments or compliments.
- Provide comments and suggestions ONLY if there is something to improve, otherwise "reviews" should be an empty array.
- Write the comment in GitHub Markdown format.
- Use the given description only for the overall context and only comment the code.
- IMPORTANT: NEVER suggest adding comments to the code.

Review the following code diff in the file "{file_path}" and take the pull request title and description into account when writing the response.
  
Pull request title: {pull.title}
Pull request description:
---
{pull.body}
---

Each line is prefixed by its number. Code to review:
```
{code}
```
"""

def create_review_prompt(pull: PullRequest, diff: str):
    """
    Creates a prompt to create a review comment.

    Args:
        pull (PullRequest): The pull request object.
        diff (str): The diff of the pull request.

    Returns:
        str: The generated prompt for review.
    """
    return f"""Your task is to review a pull request. Instructions:
- Write in name of g4f copilot. Don't use placeholder.
- Write the review in GitHub Markdown format.
- Thank the author for contributing to the project.

Pull request author: {pull.user.name}
Pull request title: {pull.title}
Pull request description:
---
{pull.body}
---

Diff:
```diff
{diff}
```
"""

def main():
    try:
        github = Github(GITHUB_TOKEN)
        pull = get_pr_details(github)
        if not pull:
            print(f"No PR number found")
            exit()
        diff = get_diff(pull.diff_url)
    except Exception as e:
        print(f"Error get details: {e.__class__.__name__}: {e}")
        exit(1)
    try:
        review = get_ai_response(create_review_prompt(pull, diff), False)
    except Exception as e:
        print(f"Error create review: {e}")
        exit(1)
    if pull.get_reviews().totalCount > 0 or pull.get_issue_comments().totalCount > 0:
        pull.create_issue_comment(body=review)
        return
    try:
        comments = analyze_code(pull, diff)
    except Exception as e:
        print(f"Error analyze: {e}")
        exit(1)
    print("Comments:", comments)
    try:
        if comments:
            pull.create_review(body=review, comments=comments)
        else:
            pull.create_issue_comment(body=review)
    except Exception as e:
        print(f"Error posting review: {e}")
        exit(1)

if __name__ == "__main__":
    main()
