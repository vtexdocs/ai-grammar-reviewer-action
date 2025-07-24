import json
import sys
import os
from pathlib import Path

ISSUE_FILE = "issues.json"
RDJSONL_FILE = "suggestions.rdjsonl"

def load_issues(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_corrections(original_line, original_pieces, corrections):
    corrected_line = original_line
    for orig, corr in zip(original_pieces, corrections):
        # Replace only the first occurrence of orig with corr in original_line
        if orig in corrected_line:
            corrected_line = corrected_line.replace(orig, corr, 1)

    return corrected_line

def filter_unchanging_issues(issues):
    for issue in issues:
        if issue["text"] == issue["correction"]:
            print(f"⚠️ [warn] Issue on line {issue['line']} has no change: '{issue['text']}'")
            continue
        yield issue

def correct_line_issues(issues, original_lines, filename):
    for issue in issues:
        line_idx = issue["line"] - 1

        if line_idx >= 0 and line_idx < len(original_lines) and issue["text"] in original_lines[line_idx]:
            # If the text is found in the specified line, we can use it directly
            yield issue
            continue

        print(f"⚠️ [warn] Text '{issue['text']}' not found in line {issue['line']} of '{filename}'.")

        line_found = False
        for i_line in original_lines:
            if issue["text"] in i_line:
                # If the text is found in another line, we can use that line instead
                corrected_line = original_lines.index(i_line) + 1
                print(f"ℹ️ [info] Using fallback for text '{issue['text']}'. Using line {corrected_line} instead of {issue['line']} in '{filename}'.")
                line_found = True

                yield {
                    "line": corrected_line,
                    "text": issue["text"],
                    "correction": issue["correction"],
                    "explanation": issue["explanation"]
                }

                break

        if not line_found:
            print(f"⚠️ [warn] Text '{issue['text']}' not found in any line of '{filename}'. Skipping issue.")
            continue

def aggregate_issues(corrected_issues, original_lines, filename):
    # Aggregate issues by line in a dict, where the key is the line number
    issues_by_line = {}
    for issue in corrected_issues:
        line = issue["line"]
        if line not in issues_by_line:
            issues_by_line[line] = []
        issues_by_line[line].append(issue)

    for line, line_issues in issues_by_line.items():
            if len(line_issues) == 1:
                yield line_issues[0]
            else:
                if line < 1 or line > len(original_lines):
                    print(f"⚠️[warn] Line {line} out of range for file '{filename}'. Skipping aggregation.")
                    continue

                explanations = "\n- " + "\n- ".join(i["explanation"] for i in line_issues)
                original_pieces = [i["text"] for i in line_issues]
                corrections = [i["correction"] for i in line_issues]

                agg_issue = {
                    "line": line,
                    "text": original_lines[line-1],
                    "correction": apply_corrections(original_lines[line-1], original_pieces, corrections),
                    "explanation": explanations
                }
                yield agg_issue

def make_rdjsonl_diagnostic(filename, issue, original_lines):
    # RDFormat expects 1-based line and column numbers
    line_idx = issue["line"] - 1
    correct_line = issue["line"]
    if line_idx < 0 or line_idx >= len(original_lines):
        # Fallback to column 1 if out of range
        start_col = 1
        end_col = 1
    else:
        text = issue["text"]
        line = original_lines[line_idx]
        # Find the first occurrence of the text to be replaced
        if text in line:
            # RDFormat counts columns using UTF-8 code points
            start_col = line.encode('utf-8').find(text.encode('utf-8')) + 1
        else:
            return {}

        end_col = start_col + len(text.encode('utf-8')) if start_col > 0 else 1
    return {
        "message": issue["explanation"],
        "location": {
            # Use absolute path so reviewdog works with RDFormat
            "path": f"{os.path.abspath(filename)}",
            "range": {
                "start": {"line": correct_line, "column": start_col},
                "end": {"line": correct_line, "column": end_col}
            }
        },
        "suggestions": [
            {
                "range": {
                    "start": {"line": correct_line, "column": start_col},
                    "end": {"line": correct_line, "column": end_col}
                },
                "text": issue["correction"]
            }
        ],
        "severity": "INFO",
    }

def main():
    issues_data = load_issues(ISSUE_FILE)
    diagnostics = []
    for filename, issues in issues_data.items():
        if not Path(filename).is_file():
            print(f"⏩[skip] File '{filename}' not found.")
            continue
        original_lines = Path(filename).read_text(encoding="utf-8").splitlines()

        # Filter out issues where the correction is the same as the original text
        filtered_issues = list(filter_unchanging_issues(issues))

        # If the text is not found in the provided line, try to find it in other lines
        # This is a fallback mechanism to ensure we can still provide a diagnostic
        corrected_issues = list(correct_line_issues(filtered_issues, original_lines, filename))

        # Multiple issues on the same line will be aggregated into a single issue
        aggregated_issues = list(aggregate_issues(corrected_issues, original_lines, filename))

        # Create RDFormat diagnostics for each aggregated issue
        for issue in aggregated_issues:
            diagnostic = make_rdjsonl_diagnostic(filename, issue, original_lines)
            if diagnostic:
                diagnostics.append(json.dumps(diagnostic, ensure_ascii=False))

    rdjsonl = "\n".join(diagnostics)
    with open(RDJSONL_FILE, "w", encoding="utf-8") as f:
        f.write(rdjsonl)
    print(f"✅[done] RDFormat suggestions written to {RDJSONL_FILE}")

if __name__ == "__main__":
    main()
