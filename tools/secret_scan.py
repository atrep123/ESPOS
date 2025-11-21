#!/usr/bin/env python3
"""Simple secret scanner for custom regex patterns.
Exit 1 if any matches found (excluding allowed test fixtures).
"""
import logging
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
IGNORE_DIRS = {'.git', 'node_modules', 'target', '.pio', '.venv', 'dist', 'build', 'reports'}
ALLOWED_FILES = {'test_fixtures/secrets.txt'}  # Example allowlist

# Regex patterns for secrets (add more as needed)
PATTERNS = {
    'AWS_ACCESS_KEY': re.compile(r'AKIA[0-9A-Z]{16}'),
    'AWS_SECRET_KEY': re.compile(r'(?<![A-Z0-9])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])'),
    'GENERIC_API_KEY': re.compile(r'api_key\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']', re.IGNORECASE),
    'BEARER_TOKEN': re.compile(r'Bearer\s+[A-Za-z0-9\-_=]{20,}\.[A-Za-z0-9\-_=]{20,}\.[A-Za-z0-9\-_=]{20,}'),
    'GOOGLE_API_KEY': re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
    'GOOGLE_OAUTH_TOKEN': re.compile(r'ya29\.[0-9A-Za-z\-_]{30,}'),
    'OAUTH_REFRESH': re.compile(r'(?i)refresh_token["\']?\s*[:=]\s*["\'][0-9A-Za-z\-_\.]{30,}["\']'),
    'PRIVATE_KEY_HEADER': re.compile(r'-----BEGIN (EC|RSA|OPENSSH|DSA|PRIVATE) KEY-----'),
}

matches = []

def should_scan(path: Path) -> bool:
    if any(p in IGNORE_DIRS for p in path.parts):
        return False
    if path.is_dir():
        return False
    if path.name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf')):
        return False
    if path.suffix.lower() in {'.bin', '.exe', '.dll', '.so'}:
        return False
    return True

for file_path in ROOT.rglob('*'):
    if not should_scan(file_path):
        continue
    rel = file_path.relative_to(ROOT).as_posix()
    if rel in ALLOWED_FILES:
        continue
    try:
        text = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for name, pattern in PATTERNS.items():
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                matches.append((name, rel, line_no, line.strip()))

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

if matches:
    logging.error('Secret scan FAILED: potential secrets detected')
    for name, rel, ln, line in matches:
        logging.error('[%s] %s:%s => %s', name, rel, ln, line)
    sys.exit(1)
else:
    logging.info('Secret scan PASS (no matches)')
