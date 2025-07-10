import os
import json
import requests
from github import Github
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_EVENT_PATH = os.environ.get('GITHUB_EVENT_PATH')

# Load PR info
event = {}
if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
    with open(GITHUB_EVENT_PATH, 'r') as f:
        event = json.load(f)
pr_number = event.get('pull_request', {}).get('number')
repo_name = event.get('repository', {}).get('full_name')

# Find changed markdown files
def get_changed_md_files():
    valid_folders = ('docs/guides', 'docs/troubleshooting', 'docs/faststore', 'docs/release-notes')

    files = []
    if 'pull_request' in event:
        files_url = event['pull_request']['url'] + '/files'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        resp = requests.get(files_url, headers=headers)
        for file in resp.json():
            if file['filename'].endswith(('.md','.mdx')) and file['filename'].startswith(valid_folders):
                files.append(file['filename'])
    return files

def review_grammar(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Add line numbers to each line
    numbered_content = ''.join(f"{i+1}: {line}" for i, line in enumerate(lines))

    response_schema = {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "integer"},
                        "text": {"type": "string"},
                        "correction": {"type": "string"},
                        "explanation": {"type": "string"}
                    },
                    "required": ["line", "text", "correction", "explanation"]
                }
            },
            "summary": {"type": "string"}
        },
        "required": ["issues", "summary"]
    }

    prompt = (
        "Review the following Markdown for grammar issues. "
        "Each line is prefixed with its line number, in the format `[line_number]: [content]`. For example: `1: This is the first line.` "
        "When reporting issues, use the provided line numbers. "
        "Return a JSON object with an 'issues' array (each with line, text, correction, explanation) and a 'summary' string.\n\n"
        f"{numbered_content}"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
            "response_schema": response_schema
        }
    )
    try:
        return response.text
    except Exception:
        return "No review returned."

def post_pr_comment(body):
    if not (GITHUB_TOKEN and repo_name and pr_number):
        print("Missing GitHub context for commenting.")
        return
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(body)

def main():
    files = get_changed_md_files()
    if not files:
        print("No Markdown files changed.")
        return
    all_issues = {}
    summaries = []
    for file in files:
        if os.path.exists(file):
            review = review_grammar(file)
            try:
                review_json = json.loads(review)
            except Exception:
                continue
            # Collect issues for this file
            all_issues[file] = review_json.get("issues", [])
            # Get only the summary to post as a PR comment
            summary = review_json.get("summary", "")
            if summary:
                summaries.append(f"### Review for `{file}`\n{summary}")


    # Post one comment with all summaries and feedback
    if summaries:
        feedback = "\n\n<hr><h2 id=\"ai-feedback\">Was this feedback useful?</h2>\n\n- [ ] Yes\n- [ ] No"
        full_comment = "## Grammar review summary\n\n" + "\n\n".join(summaries) + feedback
        post_pr_comment(full_comment)

    # Write all issues to a single issues.json file
    with open("issues.json", "w", encoding="utf-8") as f:
        json.dump(all_issues, f, indent=2)

    print("✅ Grammar review completed. Issues saved to issues.json.")

if __name__ == "__main__":
    main()
