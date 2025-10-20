"""
Diff Generator
Creates visual diffs for documentation changes
Supports HTML with red (deletions) and green (additions) highlighting
"""

import difflib
import html
import re
from typing import List, Tuple


def generate_html_diff(
    original: str, modified: str, title: str = "Documentation Changes"
) -> str:
    """
    Generate HTML diff with red/green highlighting
    Red = deletions from original
    Green = additions in modified
    """

    # Split into lines for better diff granularity
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    # Build HTML
    html_parts = [
        """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 20px 30px;
            border-bottom: 3px solid #3498db;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .stats {{
            margin-top: 10px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stats span {{
            margin-right: 20px;
        }}
        .additions {{ color: #27ae60; }}
        .deletions {{ color: #e74c3c; }}
        .view-toggle {{
            padding: 15px 30px;
            background: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
        }}
        .view-toggle button {{
            padding: 8px 16px;
            margin-right: 10px;
            border: none;
            background: #3498db;
            color: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .view-toggle button:hover {{
            background: #2980b9;
        }}
        .view-toggle button.active {{
            background: #27ae60;
        }}
        .diff-container {{
            padding: 30px;
        }}
        .side-by-side {{
            display: none;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .side-by-side.active {{
            display: grid;
        }}
        .unified {{
            display: none;
        }}
        .unified.active {{
            display: block;
        }}
        .diff-panel {{
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }}
        .panel-header {{
            background: #34495e;
            color: white;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 14px;
        }}
        .panel-content {{
            padding: 20px;
            background: #fafafa;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 600px;
            overflow-y: auto;
        }}
        .diff-line {{
            padding: 2px 5px;
            margin: 0;
            border-left: 3px solid transparent;
        }}
        .diff-add {{
            background-color: #d4edda;
            border-left-color: #27ae60;
        }}
        .diff-del {{
            background-color: #f8d7da;
            border-left-color: #e74c3c;
            text-decoration: line-through;
        }}
        .diff-change {{
            background-color: #fff3cd;
            border-left-color: #f39c12;
        }}
        .diff-unchanged {{
            background-color: transparent;
        }}
        .inline-add {{
            background-color: #a8e6a8;
            padding: 2px 4px;
            border-radius: 2px;
            font-weight: bold;
        }}
        .inline-del {{
            background-color: #ffb3b3;
            padding: 2px 4px;
            border-radius: 2px;
            text-decoration: line-through;
            font-weight: bold;
        }}
        .line-number {{
            display: inline-block;
            width: 50px;
            text-align: right;
            color: #7f8c8d;
            margin-right: 15px;
            user-select: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="stats">
                <span class="additions">● <span id="additions-count">0</span> additions</span>
                <span class="deletions">● <span id="deletions-count">0</span> deletions</span>
            </div>
        </div>
        <div class="view-toggle">
            <button onclick="showView('side-by-side')" id="btn-side" class="active">Side-by-Side</button>
            <button onclick="showView('unified')" id="btn-unified">Unified Diff</button>
        </div>
        <div class="diff-container">
""".format(
            title=html.escape(title)
        )
    ]

    # Side-by-side view
    html_parts.append('<div class="side-by-side active">')

    # Original panel
    html_parts.append(
        """
            <div class="diff-panel">
                <div class="panel-header">Original</div>
                <div class="panel-content" id="original-content">
"""
    )

    for i, line in enumerate(original_lines, 1):
        escaped_line = html.escape(line.rstrip("\n"))
        html_parts.append(
            f'<div class="diff-line diff-unchanged"><span class="line-number">{i}</span>{escaped_line}</div>\n'
        )

    html_parts.append(
        """
                </div>
            </div>
"""
    )

    # Modified panel
    html_parts.append(
        """
            <div class="diff-panel">
                <div class="panel-header">Modified (New Version)</div>
                <div class="panel-content" id="modified-content">
"""
    )

    for i, line in enumerate(modified_lines, 1):
        escaped_line = html.escape(line.rstrip("\n"))
        html_parts.append(
            f'<div class="diff-line diff-unchanged"><span class="line-number">{i}</span>{escaped_line}</div>\n'
        )

    html_parts.append(
        """
                </div>
            </div>
        </div>
"""
    )

    # Unified diff view
    html_parts.append('<div class="unified">')
    html_parts.append(
        """
            <div class="diff-panel">
                <div class="panel-header">Unified Diff</div>
                <div class="panel-content">
"""
    )

    # Generate unified diff with inline highlighting
    unified_diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            lineterm="",
            fromfile="Original",
            tofile="Modified",
            n=3,
        )
    )

    line_num_old = 0
    line_num_new = 0

    for line in unified_diff:
        if line.startswith("---") or line.startswith("+++"):
            # Skip file headers
            continue
        elif line.startswith("@@"):
            # Hunk header
            html_parts.append(
                f'<div class="diff-line diff-change"><strong>{html.escape(line)}</strong></div>\n'
            )
            # Parse line numbers
            match = re.search(r"-(\d+),\d+ \+(\d+),\d+", line)
            if match:
                line_num_old = int(match.group(1))
                line_num_new = int(match.group(2))
        elif line.startswith("-"):
            # Deletion
            escaped_line = html.escape(line[1:].rstrip("\n"))
            html_parts.append(
                f'<div class="diff-line diff-del"><span class="line-number">{line_num_old}</span><span class="inline-del">{escaped_line}</span></div>\n'
            )
            line_num_old += 1
        elif line.startswith("+"):
            # Addition
            escaped_line = html.escape(line[1:].rstrip("\n"))
            html_parts.append(
                f'<div class="diff-line diff-add"><span class="line-number">{line_num_new}</span><span class="inline-add">{escaped_line}</span></div>\n'
            )
            line_num_new += 1
        elif line.startswith(" "):
            # Unchanged context
            escaped_line = html.escape(line[1:].rstrip("\n"))
            html_parts.append(
                f'<div class="diff-line diff-unchanged"><span class="line-number">{line_num_old}/{line_num_new}</span>{escaped_line}</div>\n'
            )
            line_num_old += 1
            line_num_new += 1

    html_parts.append(
        """
                </div>
            </div>
        </div>
"""
    )

    html_parts.append(
        """
        </div>
    </div>
    <script>
        function showView(view) {
            // Hide all views
            document.querySelectorAll('.side-by-side, .unified').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.view-toggle button').forEach(el => el.classList.remove('active'));

            // Show selected view
            if (view === 'side-by-side') {
                document.querySelector('.side-by-side').classList.add('active');
                document.getElementById('btn-side').classList.add('active');
            } else {
                document.querySelector('.unified').classList.add('active');
                document.getElementById('btn-unified').classList.add('active');
            }
        }

        // Calculate stats
        window.addEventListener('load', () => {
            const additions = document.querySelectorAll('.diff-add, .inline-add').length;
            const deletions = document.querySelectorAll('.diff-del, .inline-del').length;
            document.getElementById('additions-count').textContent = additions;
            document.getElementById('deletions-count').textContent = deletions;
        });
    </script>
</body>
</html>
"""
    )

    return "".join(html_parts)


def generate_jira_description_diff(original: str, modified: str) -> str:
    """
    Generate a text-based diff suitable for Jira ticket descriptions
    Uses emoji and text formatting
    """

    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    diff_lines = []
    diff_lines.append("📝 Documentation Changes Summary\n")
    diff_lines.append("━" * 50)
    diff_lines.append("")

    # Use SequenceMatcher for better word-level diffs
    sm = difflib.SequenceMatcher(None, original_lines, modified_lines)

    additions = 0
    deletions = 0
    changes = 0

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "delete":
            deletions += i2 - i1
            diff_lines.append(f"🔴 REMOVED (lines {i1+1}-{i2}):")
            for line in original_lines[i1:i2]:
                diff_lines.append(f"  - {line}")
            diff_lines.append("")

        elif tag == "insert":
            additions += j2 - j1
            diff_lines.append(f"🟢 ADDED (lines {j1+1}-{j2}):")
            for line in modified_lines[j1:j2]:
                diff_lines.append(f"  + {line}")
            diff_lines.append("")

        elif tag == "replace":
            changes += 1
            diff_lines.append(f"🟡 CHANGED (lines {i1+1}-{i2}):")
            diff_lines.append("  Old:")
            for line in original_lines[i1:i2]:
                diff_lines.append(f"    - {line}")
            diff_lines.append("  New:")
            for line in modified_lines[j1:j2]:
                diff_lines.append(f"    + {line}")
            diff_lines.append("")

    # Summary
    diff_lines.append("━" * 50)
    diff_lines.append(
        f"📊 Summary: {additions} additions, {deletions} deletions, {changes} changes"
    )

    return "\n".join(diff_lines)


def detect_image_references(content: str) -> List[Tuple[str, str]]:
    """
    Detect image references in markdown content
    Returns list of (alt_text, image_url) tuples
    """

    images = []

    # Markdown images: ![alt](url)
    markdown_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content)
    images.extend(markdown_images)

    # HTML img tags
    html_images = re.findall(
        r'<img[^>]+alt=["\']([^"\']*)["\'][^>]+src=["\']([^"\']+)["\']', content
    )
    images.extend(html_images)

    html_images2 = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+alt=["\']([^"\']*)["\']', content
    )
    images.extend([(alt, src) for src, alt in html_images2])

    return images


def compare_image_references(original: str, modified: str) -> dict:
    """
    Compare image references between original and modified content
    Returns dict with added, removed, and unchanged images
    """

    original_images = set(detect_image_references(original))
    modified_images = set(detect_image_references(modified))

    return {
        "added": list(modified_images - original_images),
        "removed": list(original_images - modified_images),
        "unchanged": list(original_images & modified_images),
    }
