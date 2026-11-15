"""Read-only, module-local AST and Markdown analysis."""
import ast
import os
from pathlib import Path
import re

from .phrases import FINANCIALDOCUMENTEXTRACTION, NOFINANCIALDOCUMENTEXTRACTION, GENERIC_NAMES

POSITIVE_RULE = 'documented-financial-document-extraction-claim-false'
NEGATIVE_RULE = 'documented-no-financial-document-extraction-claim-false'


def normalize(text):
    return ' '.join(text.lower().replace("n't", ' not').replace('-', ' ').split())


def prose_paragraphs(text):
    lines = []
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        if fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*$', line):
                fence = None
            lines.append((number, ''))
            continue
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if match and not (match[1][0] == '`' and '`' in match[2]):
            fence = (match[1][0], len(match[1]))
            lines.append((number, ''))
        else:
            lines.append((number, line))
    paragraph = []
    start = 1
    for number, line in lines + [(len(lines) + 1, '')]:
        if not line.strip():
            if paragraph:
                yield start, normalize(' '.join(paragraph))
                paragraph = []
        else:
            if not paragraph:
                start = number
            paragraph.append(line)


def phrase_matches(text, phrases):
    # Consume longest matches first, avoiding overlap between nested phrases.
    remaining = text
    found = []
    for phrase in sorted(phrases, key=lambda s: (-len(s), s)):
        pattern = r'\b' + re.escape(phrase) + r'\b'
        matches = list(re.finditer(pattern, remaining))
        if matches:
            found.extend(phrase for _ in matches)
            remaining = re.sub(pattern, lambda m: ' ' * len(m[0]), remaining)
    return found, remaining


def claims_in(text, path='README.md'):
    claims = []
    for line, paragraph in prose_paragraphs(text):
        denials, rest = phrase_matches(paragraph, NOFINANCIALDOCUMENTEXTRACTION)
        positives, _ = phrase_matches(rest, FINANCIALDOCUMENTEXTRACTION)
        for family, matches in [('NOFINANCIALDOCUMENTEXTRACTION', denials),
                                ('FINANCIALDOCUMENTEXTRACTION', positives)]:
            for phrase in matches:
                claims.append(dict(family=family, phrase=phrase, path=str(path), line=line))
    return claims


def module_evidence(source):
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    nodes = list(ast.walk(tree))
    imports = {}
    mindee = False
    shadow = set()
    definitions = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                mindee |= alias.name.split('.')[0] == 'mindee'
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            mindee |= module.split('.')[0] == 'mindee' and not node.level
            for alias in node.names:
                imports[alias.asname or alias.name] = module + '.' + alias.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadow.add(node.name)
            definitions.add(node.name)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars]
        for target in targets:
            shadow.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
    def resolved(node):
        if isinstance(node, ast.Name):
            return '' if node.id in shadow else imports.get(node.id, '')
        if isinstance(node, ast.Attribute):
            base = resolved(node.value)
            return base + '.' + node.attr if base else ''
        return ''
    def clean(node):
        return not any(isinstance(n, ast.Name) and n.id in shadow and (n.id in imports or n.id in definitions or n.id in GENERIC_NAMES or n.id in {'mindee', 'FinancialDocumentV1', 'Client'}) for n in ast.walk(node))
    def named(node, name):
        return ((isinstance(node, ast.Name) and node.id == name) or
                (isinstance(node, ast.Attribute) and node.attr == name)) and name not in shadow and clean(node)
    calls = [n for n in nodes if isinstance(n, ast.Call)]
    client = mindee and 'Client' not in shadow and any(
        (resolved(c.func) == 'mindee.Client' and clean(c.func)) or
        (isinstance(c.func, ast.Attribute) and c.func.attr == 'Client' and
         isinstance(c.func.value, ast.Name) and c.func.value.id == 'mindee' and
         'Client' not in shadow and clean(c.func)) for c in calls)
    evidence = []
    for call in calls:
        func = call.func
        generic = False
        if isinstance(func, ast.Attribute):
            generic = func.attr in GENERIC_NAMES and func.attr not in shadow
        elif isinstance(func, ast.Name):
            target = resolved(func)
            generic = bool(target) and target.rsplit('.', 1)[-1] in GENERIC_NAMES and target.rsplit('.', 1)[-1] not in shadow
        if generic and clean(func):
            evidence.append(dict(route='generic', line=call.lineno))
        if (client and isinstance(func, ast.Attribute) and func.attr == 'parse' and
                'parse' not in shadow and clean(func) and
                any(named(arg, 'FinancialDocumentV1') for arg in
                    list(call.args) + [kw.value for kw in call.keywords])):
            evidence.append(dict(route='mindee', line=call.lineno))
    return evidence


def audit(root, ignore=()):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise OSError('Repository must be an existing, readable, non-symlink directory')
    prefixes = [Path(p).as_posix().strip('/') for p in ignore]
    def ignored(rel):
        value = rel.as_posix()
        return any(p in ('', '.') or value == p or value.startswith(p + '/') for p in prefixes)
    claims, evidence = [], []
    def walk_error(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink()
                         and not ignored((Path(directory) / d).relative_to(root)))
        for filename in sorted(files):
            path = Path(directory) / filename
            rel = path.relative_to(root)
            if path.is_symlink() or ignored(rel):
                continue
            if rel.as_posix() == 'README.md' or (path.suffix == '.md' and 'docs' in rel.parts[:-1]):
                claims.extend(claims_in(path.read_text(encoding='utf-8'), rel))
            if path.suffix != '.py' or {'fixtures', 'docs', 'examples'}.intersection(rel.parts[:-1]):
                continue
            is_test = 'tests' in rel.parts[:-1] or filename.startswith('test_') or filename.endswith('_test.py')
            for item in module_evidence(path.read_text(encoding='utf-8')):
                evidence.append(dict(item, path=rel.as_posix(), test=is_test))
    production = any(not e['test'] for e in evidence)
    findings = []
    positive = any(c['family'] == 'FINANCIALDOCUMENTEXTRACTION' for c in claims)
    negative = any(c['family'] == 'NOFINANCIALDOCUMENTEXTRACTION' for c in claims)
    if positive and not production:
        severity = 'MEDIUM' if evidence else 'HIGH'
        findings.append(dict(rule=POSITIVE_RULE, severity=severity,
                             message='Documented capability has only test evidence.' if evidence else 'Documented capability has no production evidence.'))
    if negative and production:
        findings.append(dict(rule=NEGATIVE_RULE, severity='HIGH', message='Documented denial conflicts with production evidence.'))
    return dict(verdict='FAIL' if findings else 'PASS', findings=findings, claims=claims, evidence=evidence)
