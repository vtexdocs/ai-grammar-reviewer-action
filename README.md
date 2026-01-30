# AI Grammar Reviewer Action

A GitHub Action that integrates with Google Gemini AI to automatically make grammar reviews in Markdown files of pull requests (PRs).

## How it works

This action executes a series of steps to read the Markdown files, use Google Gemini AI to review them, save the review data in temporary files, and post the review in two forms: summary comment and inline suggestions.

### Summary comment

The summary comment is a single comment in the PR formatted in Markdown and HTML including a summary of the review for each file reviewed. It also has a feedback option, which is collected by another action.

![Summary comment example](./images/summary-comment-example.png)

### Inline suggestions

Inline suggestions appear in the file diffs, so they can be [easily applied](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request). The action uses [reviewdog](https://github.com/reviewdog/reviewdog) to post suggestions. The action posts one suggestion per line where Gemini identifies an issue.

![Inline suggestion example](./images/inline-suggestion-example.png)

When issues occur outside the scope of the content changed in the PR (diff hunk), inline suggestions cannot be posted due to a [GitHub limitation](https://github.com/microsoft/vscode-pull-request-github/issues/172). Instead, reviewdog post them as comments for the file. The issue line is still indicated in the comment.

![Comment outside diff example](images/comment-outside-diff-example.png)

## Action usage

To use this action in your GitHub repository, follow these steps:

1. Get a [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key) in [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Add your key as a [secret to your repository](https://docs.github.com/en/codespaces/managing-codespaces-for-your-organization/managing-development-environment-secrets-for-your-repository-or-organization#adding-secrets-for-a-repository).
3. Create the workflow file for your repository in the `.github/workflows` folder. It will use the secret with the same name you chose in the repository configuration (e.g., `GEMINI_API_KEY`). Here is an example of workflow configuration:

    ```yml
      name: AI Grammar Reviewer

      on:
        pull_request:
          paths:
            - 'docs/**/*.md'
            - 'docs/**/*.mdx'
          types: [opened, synchronize]

      permissions:
        contents: read
        pull-requests: write

      jobs:
        grammar-review:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@v4
            - uses: vtexdocs/ai-grammar-reviewer-action@v0
              with:
                gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
                github_token: ${{ secrets.GITHUB_TOKEN }}
    ```

    The `folders` input is optional. When omitted, only changed files under `docs/` are reviewed. To restrict or extend which paths are reviewed, pass `folders` as a newline- or comma-separated list of folder prefixes (e.g. `docs`, `docs/guides`, `docs/release-notes`):

    ```yml
            - uses: vtexdocs/ai-grammar-reviewer-action@v0
              with:
                gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
                github_token: ${{ secrets.GITHUB_TOKEN }}
                folders: |
                  docs/guides
                  docs/release-notes
    ```

## Review tips

Here are some tips to improve the review process with this action.

### Apply suggestions in batch

When the action makes many suggestions, instead of applying suggestions individually, add them to a batch and make a single commit. To do this, follow these steps:

1. Click on the **Files changed** tab in your PR.
2. On each suggestion you want to apply, click on **Add suggestion to batch**.
3. Click **Commit suggestions** at the top of the page.
4. In the two text boxes, edit the commit name and description if you want.
5. Click **Commit changes**.

![Commit suggestions in batch](./images/batch-commit.gif)

### Run the reviewer multiple times

The AI model is not perfect. It is common for it to give only part of the suggestions it should on each execution.

If the action is configured to run on `synchronize`, it will run for every change on the PR. So, after applying the suggestions, wait for the action to run again, check the new suggestions and apply those you want. Repeat this process as many times as needed.

You can also [re-run the jobs manually](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs). You can use this to generate the suggestions again without making any changes to the PR content.

## Internal workings

The action runs from a Dockerfile that calls a shell script. This script has the following steps:

1. Execute a Python script for the Gemini grammar review (`grammar_reviewer.py`). It has these steps:
    1. Retrieve the content of the Markdown files.
    2. For each file, call the Gemini API with the grammar review prompt. The request uses a JSON schema parameter to format the response in a specific JSON format. This response includes:
        - A list of objects for each issue, whose field are the line number, the original content, the suggested correction, and an explanation for the correction.
        - A string with the summary of the file review.
    3. Write the lists of issues in a JSON file (`issues.json`), which will be used for the next python script to post the suggestions.
    4. Aggregate the review summaries and use the GitHub API to post them as a single comment along with the feedback option.
2. Verify if the `issues.json` file exists. If true, execute a Python script (`generate_rdjsonl.py`) to convert the issues JSON to a format that reviewdog accepts and creates another file (`suggestions.rdjsonl`). It uses [RDFormat with rdjsonl](https://github.com/reviewdog/reviewdog/tree/master/proto/rdf#rdjsonl). This script applies the following changes in the issues list before converting to RDFormat:
    - Remove issues where the corrected text is equal to the original.
    - If the original text is not found in the provided line number, try to find it in another line and update the line number. If it still isn't found, remove the issue.
    - Aggregate issues in the same line into a single issue. When there are multiple issues in the same line, the explanation is posted as an unordered list.

> [!NOTE]
> The character/column count in RDFormat is different from the traditional byte count, since it uses UTF-8 encoding internally. This difference occurs with emojis and some special characters (e.g., `’`).

3. Verify if the `suggestions.rdjsonl` file exists. If true, execute reviewdog to post suggestions.

```mermaid
flowchart LR
    A(["Start"]) --> B["Gemini grammar<br/>review"]
    B --issues.json--> C{"File exists?"}
    B --> D["Post comment with<br/>summary comment<br/>and feedback option"]
    C --Yes--> E["Convert JSON to<br/>RDFormat (rdjsonl)"]
    C --No --> F["Skip script"]
    E --suggestions.rdjsonl--> G{"File exists?"}
    F --> G{"File exists?"}
    G --Yes--> H["Reviewdog post<br/>suggestions"]
    G --No --> I["Skip reviewdog"]
    H & I --> J(["End"])
```
