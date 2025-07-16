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

def get_utf16_col(line, substring):
    """Return the 1-based UTF-16 code unit column for the first occurrence of substring in line."""
    idx = line.find(substring)
    if idx == -1:
        return None
    # Count UTF-16 code units up to idx
    prefix = line[:idx]
    utf16_units = len(prefix.encode('utf-16-le')) // 2  # 2 bytes per code unit
    return utf16_units + 1  # RDFormat columns are 1-based

def make_rdjsonl_diagnostic(filename, issue, original_lines):
    # RDFormat expects 1-based line and column numbers
    line_idx = issue["line"] - 1
    if line_idx < 0 or line_idx >= len(original_lines):
        # fallback to column 1 if out of range
        start_col = 1
        end_col = 1
    else:
        text = issue["text"]
        line = original_lines[line_idx]
        col = get_utf16_col(line, text)
        if col is None:
            print(f"⚠️[warn] Text '{text}' not found in line {issue['line']} of '{filename}'.")
            return {}
        # Calculate end column in UTF-16 code units
        text_utf16_len = len(text.encode('utf-16-le')) // 2
        start_col = col
        end_col = start_col + text_utf16_len
    return {
        "message": issue["explanation"],
        "location": {
            # Use absolute path so reviewdog works with RDFormat
            "path": f"{os.path.abspath(filename)}",
            "range": {
                "start": {"line": issue["line"], "column": start_col},
                "end": {"line": issue["line"], "column": end_col}
            }
        },
        "suggestions": [
            {
                "range": {
                    "start": {"line": issue["line"], "column": start_col},
                    "end": {"line": issue["line"], "column": end_col}
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
        # Aggregate issues by line in a dict, where the key is the line number
        issues_by_line = {}
        for issue in issues:
            line = issue["line"]
            if line not in issues_by_line:
                issues_by_line[line] = []
            issues_by_line[line].append(issue)
        aggregated_issues = []

        for line, line_issues in issues_by_line.items():
            if len(line_issues) == 1:
                aggregated_issues.append(line_issues[0])
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
                aggregated_issues.append(agg_issue)

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
