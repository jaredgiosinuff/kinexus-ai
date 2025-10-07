/**
 * Document Service - Handles document operations and diff processing
 */

export interface DiffLine {
  type: 'added' | 'removed' | 'unchanged' | 'header' | 'hunk';
  oldLineNumber?: number;
  newLineNumber?: number;
  content: string;
  highlight?: boolean;
}

export interface ParsedDiff {
  lines: DiffLine[];
  stats: {
    additions: number;
    deletions: number;
    total: number;
  };
  hunks: Array<{
    oldStart: number;
    oldLines: number;
    newStart: number;
    newLines: number;
    lines: DiffLine[];
  }>;
}

export interface DocumentVersion {
  id: string;
  version: string;
  content: string;
  timestamp: Date;
  author: string;
  changes: string[];
}

class DocumentService {
  /**
   * Parse unified diff format into structured data
   */
  parseDiff(diffContent: string): ParsedDiff {
    const lines = diffContent.split('\n');
    const parsedLines: DiffLine[] = [];
    const hunks: ParsedDiff['hunks'] = [];

    let oldLineNum = 1;
    let newLineNum = 1;
    let additions = 0;
    let deletions = 0;
    let currentHunk: ParsedDiff['hunks'][0] | null = null;

    for (const line of lines) {
      if (line.startsWith('@@')) {
        // Hunk header: @@ -oldStart,oldLines +newStart,newLines @@
        const match = line.match(/@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)/);
        if (match) {
          const oldStart = parseInt(match[1]);
          const oldLines = parseInt(match[2] || '1');
          const newStart = parseInt(match[3]);
          const newLines = parseInt(match[4] || '1');
          const context = match[5]?.trim() || '';

          oldLineNum = oldStart;
          newLineNum = newStart;

          currentHunk = {
            oldStart,
            oldLines,
            newStart,
            newLines,
            lines: []
          };
          hunks.push(currentHunk);

          const hunkLine: DiffLine = {
            type: 'hunk',
            content: `${line}${context ? ` ${context}` : ''}`,
          };
          parsedLines.push(hunkLine);
          currentHunk.lines.push(hunkLine);
        }
      } else if (line.startsWith('+++') || line.startsWith('---')) {
        // File headers
        const diffLine: DiffLine = {
          type: 'header',
          content: line,
        };
        parsedLines.push(diffLine);
      } else if (line.startsWith('+')) {
        // Added line
        const diffLine: DiffLine = {
          type: 'added',
          newLineNumber: newLineNum++,
          content: line.substring(1),
        };
        parsedLines.push(diffLine);
        currentHunk?.lines.push(diffLine);
        additions++;
      } else if (line.startsWith('-')) {
        // Removed line
        const diffLine: DiffLine = {
          type: 'removed',
          oldLineNumber: oldLineNum++,
          content: line.substring(1),
        };
        parsedLines.push(diffLine);
        currentHunk?.lines.push(diffLine);
        deletions++;
      } else if (line.startsWith(' ') || line === '') {
        // Unchanged line
        const diffLine: DiffLine = {
          type: 'unchanged',
          oldLineNumber: oldLineNum++,
          newLineNumber: newLineNum++,
          content: line.substring(1),
        };
        parsedLines.push(diffLine);
        currentHunk?.lines.push(diffLine);
      }
    }

    return {
      lines: parsedLines,
      stats: {
        additions,
        deletions,
        total: additions + deletions,
      },
      hunks,
    };
  }

  /**
   * Generate a simple diff between two text strings
   */
  generateSimpleDiff(oldContent: string, newContent: string): string {
    const oldLines = oldContent.split('\n');
    const newLines = newContent.split('\n');

    // Simple line-by-line diff (could be enhanced with proper diff algorithm)
    const diffLines: string[] = [];
    const maxLines = Math.max(oldLines.length, newLines.length);

    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i];
      const newLine = newLines[i];

      if (oldLine === undefined) {
        // Line added
        diffLines.push(`+${newLine}`);
      } else if (newLine === undefined) {
        // Line removed
        diffLines.push(`-${oldLine}`);
      } else if (oldLine !== newLine) {
        // Line changed
        diffLines.push(`-${oldLine}`);
        diffLines.push(`+${newLine}`);
      } else {
        // Line unchanged
        diffLines.push(` ${oldLine}`);
      }
    }

    return diffLines.join('\n');
  }

  /**
   * Extract and highlight changes in diff content
   */
  highlightChanges(diffContent: string, searchTerm?: string): ParsedDiff {
    const parsed = this.parseDiff(diffContent);

    if (searchTerm) {
      // Highlight search terms
      const regex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');

      parsed.lines.forEach(line => {
        if (regex.test(line.content)) {
          line.highlight = true;
        }
      });
    }

    return parsed;
  }

  /**
   * Get diff statistics summary
   */
  getDiffStats(diffContent: string): {
    files: number;
    additions: number;
    deletions: number;
    changes: number;
  } {
    const parsed = this.parseDiff(diffContent);
    const fileHeaders = parsed.lines.filter(line =>
      line.type === 'header' && (line.content.startsWith('+++') || line.content.startsWith('---'))
    );

    return {
      files: Math.ceil(fileHeaders.length / 2), // +++ and --- come in pairs
      additions: parsed.stats.additions,
      deletions: parsed.stats.deletions,
      changes: parsed.stats.total,
    };
  }

  /**
   * Format diff for display with syntax highlighting
   */
  formatDiffForDisplay(diffContent: string): Array<{
    lineNumber: string;
    type: 'added' | 'removed' | 'unchanged' | 'header';
    content: string;
    className: string;
  }> {
    const parsed = this.parseDiff(diffContent);

    return parsed.lines.map(line => {
      let lineNumber = '';
      if (line.oldLineNumber && line.newLineNumber) {
        lineNumber = `${line.oldLineNumber}-${line.newLineNumber}`;
      } else if (line.oldLineNumber) {
        lineNumber = `${line.oldLineNumber}-`;
      } else if (line.newLineNumber) {
        lineNumber = `-${line.newLineNumber}`;
      }

      const className = `diff-line diff-line-${line.type}${line.highlight ? ' diff-line-highlight' : ''}`;

      return {
        lineNumber,
        type: line.type,
        content: line.content,
        className,
      };
    });
  }

  /**
   * Extract context around changes
   */
  extractChangeContext(diffContent: string, contextLines: number = 3): ParsedDiff {
    const parsed = this.parseDiff(diffContent);
    const relevantLines: DiffLine[] = [];

    // Find all change lines
    const changeIndices: number[] = [];
    parsed.lines.forEach((line, index) => {
      if (line.type === 'added' || line.type === 'removed') {
        changeIndices.push(index);
      }
    });

    // Collect context around changes
    const includedIndices = new Set<number>();

    changeIndices.forEach(changeIndex => {
      for (let i = Math.max(0, changeIndex - contextLines);
           i <= Math.min(parsed.lines.length - 1, changeIndex + contextLines);
           i++) {
        includedIndices.add(i);
      }
    });

    // Build final lines array
    const sortedIndices = Array.from(includedIndices).sort((a, b) => a - b);
    sortedIndices.forEach(index => {
      relevantLines.push(parsed.lines[index]);
    });

    return {
      ...parsed,
      lines: relevantLines,
    };
  }

  /**
   * Validate document format
   */
  validateDocument(content: string, fileType: string): {
    valid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Basic validation
    if (!content || content.trim().length === 0) {
      errors.push('Document content is empty');
    }

    // File type specific validation
    switch (fileType.toLowerCase()) {
      case 'markdown':
      case 'md':
        if (!content.includes('#')) {
          warnings.push('No headers found in Markdown document');
        }
        break;

      case 'json':
        try {
          JSON.parse(content);
        } catch (e) {
          errors.push('Invalid JSON format');
        }
        break;

      case 'yaml':
      case 'yml':
        // Basic YAML validation (could use a proper YAML parser)
        if (content.includes('\t')) {
          errors.push('YAML files should not contain tabs');
        }
        break;
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Get document preview (first few lines)
   */
  getDocumentPreview(content: string, maxLines: number = 10): string {
    const lines = content.split('\n');
    return lines.slice(0, maxLines).join('\n');
  }

  /**
   * Generate document summary
   */
  generateDocumentSummary(content: string): {
    wordCount: number;
    lineCount: number;
    characterCount: number;
    estimatedReadTime: number; // in minutes
  } {
    const lines = content.split('\n');
    const words = content.split(/\s+/).filter(word => word.length > 0);
    const characters = content.length;

    // Estimate reading time (average 200 words per minute)
    const estimatedReadTime = Math.ceil(words.length / 200);

    return {
      wordCount: words.length,
      lineCount: lines.length,
      characterCount: characters,
      estimatedReadTime,
    };
  }
}

export const documentService = new DocumentService();