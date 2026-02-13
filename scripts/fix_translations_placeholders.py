#!/usr/bin/env python3
"""
Fix placeholder-name mismatches between msgid and msgstr in a .po file.

This is a best-effort script that will:
 - parse simple singular msgid/msgstr entries
 - detect Python-style `%(name)s` and brace-style `{name}` placeholders
 - if the counts match but names differ, map them positionally and rewrite msgstr
 - skip plural entries and entries where counts differ

Usage:
    python3 scripts/fix_translations_placeholders.py \
        --po translations/es_CL/LC_MESSAGES/messages.po

It writes a backup file next to the original (messages.po.bak) and a fixed
output file named messages.fixed.po. It also prints a short report.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple, Optional


PERCENT_RE = re.compile(r"%\(([^)]+)\)[a-zA-Z]")
BRACE_RE = re.compile(r"\{([^{}!:]+)(?:![^:}]+)?(?::[^}]+)?\}")


def extract_quoted(lines: List[str], start_idx: int) -> Tuple[str, int]:
    """Extract a possibly multi-line quoted string starting at start_idx.

    Returns (text, next_index)
    """
    first = lines[start_idx]
    # line like: msgid "..." or msgstr "..."
    m = re.search(r'\"(.*)\"', first)
    text = ''
    if m:
        text = m.group(1)
    idx = start_idx + 1
    # collect subsequent continued "..." lines
    while idx < len(lines) and lines[idx].lstrip().startswith('"'):
        m = re.search(r'\"(.*)\"', lines[idx])
        if m:
            text += m.group(1)
        idx += 1
    return text, idx


def find_placeholders(text: str) -> Tuple[str, List[str]]:
    """Return style ("percent"|"brace"|"none") and list of names in order."""
    p = PERCENT_RE.findall(text)
    if p:
        return 'percent', p
    b = BRACE_RE.findall(text)
    if b:
        return 'brace', b
    return 'none', []


def replace_percent_placeholders(text: str, new_names: List[str]) -> str:
    it = iter(new_names)

    def repl(m: re.Match) -> str:
        orig = m.group(0)
        # full pattern like %(name)s -> we want to replace name only
        name = m.group(1)
        try:
            target = next(it)
        except StopIteration:
            return orig
        return orig.replace(name, target, 1)

    return PERCENT_RE.sub(repl, text)


def replace_brace_placeholders(text: str, new_names: List[str]) -> str:
    it = iter(new_names)

    def repl(m: re.Match) -> str:
        inner = m.group(0)
        name = m.group(1)
        try:
            target = next(it)
        except StopIteration:
            return inner
        # replace only the first occurrence of the name inside the braces
        return inner.replace(name, target, 1)

    return BRACE_RE.sub(repl, text)


def process_po(path: Path) -> Tuple[int, int, int]:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()

    out_lines: List[str] = []
    i = 0
    total = 0
    fixed = 0
    skipped = 0

    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        if line.startswith('msgid '):
            # parse msgid
            msgid_text, ni = extract_quoted(lines, i)
            # append any intermediate lines we've already copied
            # advance to ni (we've already appended the starting msgid line)
            j = i + 1
            while j < ni:
                out_lines.append(lines[j])
                j += 1
            i = ni
            # look ahead for msgid_plural or msgstr
            has_plural = False
            msgstr_idx: Optional[int] = None
            msgstr_text = ''
            k = i
            while k < len(lines) and not lines[k].startswith('msgid '):
                if lines[k].startswith('msgid_plural'):
                    has_plural = True
                if lines[k].startswith('msgstr '):
                    msgstr_text, ni2 = extract_quoted(lines, k)
                    msgstr_idx = k
                    break
                if lines[k].startswith('msgstr['):
                    # pluralized entry - skip
                    has_plural = True
                k += 1

            if msgstr_idx is None or has_plural:
                # nothing to do; continue consuming until k or i
                i = max(i, k)
                total += 1
                skipped += 1
                continue

            total += 1
            # determine placeholders
            style_id, names_id = find_placeholders(msgid_text)
            style_str, names_str = find_placeholders(msgstr_text)

            if style_id == 'none' and style_str == 'none':
                # nothing to do
                # append the msgstr block lines
                # append msgstr line and any continued lines
                # we've not yet appended the msgstr line at msgstr_idx
                while i <= msgstr_idx:
                    out_lines.append(lines[i])
                    i += 1
                # append any continuation lines
                while i < len(lines) and lines[i].lstrip().startswith('"'):
                    out_lines.append(lines[i])
                    i += 1
                skipped += 1
                continue

            if style_id != style_str:
                # different placeholder styles; skip
                # copy through the msgstr block
                while i <= msgstr_idx:
                    out_lines.append(lines[i])
                    i += 1
                while i < len(lines) and lines[i].lstrip().startswith('"'):
                    out_lines.append(lines[i])
                    i += 1
                skipped += 1
                continue

            if len(names_id) != len(names_str):
                # counts differ; skip
                while i <= msgstr_idx:
                    out_lines.append(lines[i])
                    i += 1
                while i < len(lines) and lines[i].lstrip().startswith('"'):
                    out_lines.append(lines[i])
                    i += 1
                skipped += 1
                continue

            # perform positional mapping replacement on msgstr_text
            new_msgstr_text = msgstr_text
            if style_str == 'percent':
                new_msgstr_text = replace_percent_placeholders(msgstr_text, names_id)
            elif style_str == 'brace':
                new_msgstr_text = replace_brace_placeholders(msgstr_text, names_id)

            if new_msgstr_text != msgstr_text:
                fixed += 1
                # write the msgstr line replacing the quoted text
                prefix = lines[msgstr_idx].split('"', 1)[0]
                out_lines.append(f'{prefix}"{new_msgstr_text}"')
                # skip the original msgstr line and any continuation lines
                i = msgstr_idx + 1
                while i < len(lines) and lines[i].lstrip().startswith('"'):
                    i += 1
            else:
                # no change; copy msgstr block
                while i <= msgstr_idx:
                    out_lines.append(lines[i])
                    i += 1
                while i < len(lines) and lines[i].lstrip().startswith('"'):
                    out_lines.append(lines[i])
                    i += 1

        else:
            i += 1

    # write backup and fixed file
    bak = path.with_suffix(path.suffix + '.bak')
    if not bak.exists():
        path.replace(bak)
        # write out_lines to original path
        path.write_text('\n'.join(out_lines), encoding='utf-8')
    else:
        # original already backed up; just write fixed file
        path.write_text('\n'.join(out_lines), encoding='utf-8')

    fixed_path = path.with_name(path.stem + '.fixed' + path.suffix)
    fixed_path.write_text('\n'.join(out_lines), encoding='utf-8')

    return total, fixed, skipped


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--po', default='translations/es_CL/LC_MESSAGES/messages.po')
    args = p.parse_args()
    path = Path(args.po)
    if not path.exists():
        print(f'ERROR: .po file not found: {path}')
        raise SystemExit(2)

    print(f'Processing: {path}')
    total, fixed, skipped = process_po(path)
    print(f'Total entries examined: {total}')
    print(f'Automatically fixed:    {fixed}')
    print(f'Skipped (plural/complex): {skipped}')
    print('Wrote backup at: ' + str(path.with_suffix(path.suffix + '.bak')))
    print('Wrote fixed file at: ' + str(path.with_name(path.stem + '.fixed' + path.suffix)))


if __name__ == '__main__':
    main()
