#!/usr/bin/env python3
"""Scan curated files or Git blobs. No network/VM access; manual review required."""
import argparse
import ipaddress
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.gitignore', 'LICENSE', 'README.md', 'README.ru.md',
           'diagrams/network-topology.mmd', 'scripts/check_public.py',
           'scripts/ssh_check.py', '.github/workflows/ci.yml',
           'infra/README.md', 'infra/examples/edge-router.nft',
           'infra/libvirt/lab.sh'}
ALLOWED.update(f'docs/{lang}/{name}.md' for lang in ('en', 'ru')
               for name in ('architecture', 'validation', 'security', 'portfolio-case',
                            'infrastructure-as-code', 'ssh-hardening'))
ALLOWED.update(f'infra/libvirt/networks/lab-{name}.xml'
               for name in ('lan', 'dmz', 'wan', 'isp', 'mgmt'))
ALLOWED.update(f'infra/ansible/{name}' for name in (
    'ansible.cfg', '.ansible-lint', '.yamllint',
    'inventory/hosts.yml', 'inventory/group_vars/all.yml',
    'inventory/group_vars/routers.yml', 'inventory/group_vars/edge.yml',
    'inventory/group_vars/web.yml', 'vars/matrix.yml',
    'playbooks/site.yml', 'playbooks/bootstrap.yml', 'playbooks/ssh_hardening.yml',
    'playbooks/verify.yml', 'playbooks/audit_ssh.yml',
    'roles/packages/tasks/main.yml',
    'roles/base/tasks/main.yml', 'roles/base/handlers/main.yml',
    'roles/network/tasks/main.yml', 'roles/network/handlers/main.yml',
    'roles/network/templates/interfaces.j2',
    'roles/edge_firewall/tasks/main.yml', 'roles/edge_firewall/handlers/main.yml',
    'roles/edge_firewall/templates/rules.v4.j2',
    'roles/edge_firewall/templates/lab-firewall.service.j2',
    'roles/web/defaults/main.yml', 'roles/web/tasks/main.yml',
    'roles/web/handlers/main.yml', 'roles/web/templates/index.html.j2',
    'roles/web/templates/lab-web.service.j2',
    'roles/web_tls/defaults/main.yml', 'roles/web_tls/tasks/main.yml',
    'roles/web_tls/handlers/main.yml', 'roles/web_tls/templates/lab-web.conf.j2',
    'roles/ssh_hardening/defaults/main.yml', 'roles/ssh_hardening/tasks/main.yml',
    'roles/ssh_hardening/handlers/main.yml',
    'roles/ssh_hardening/templates/00-lab-hardening.conf.j2',
    'roles/ssh_hardening/templates/jail-lab-sshd.local.j2'))
LOCAL_ONLY = {'.git', '.agents', '.aws', '.codex', '__pycache__'}
PATTERNS = {
    'UUID': r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',
    'MAC': r'\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b',
    'personal or privileged path': r'/(?:home|Users|root)/',
    'private key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'credential assignment': r'\b(?:password|passwd|token|api[_-]?key|secret)\s*[:=]\s*[\w/+.-]{4,}',
    'GitHub credential': r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    'cloud access identifier': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'credential URL': r'https?://[^\s/@]+:[^\s/@]+@',
    'IPv6 address': (r'(?<![\w:])(?:(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}'
                     r'|(?:[0-9a-f]{1,4}:){1,6}:(?:[0-9a-f]{1,4})?'
                     r'|::(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})(?![\w:])'),
}
# Not host addresses: the wildcard bind address and the netmask of the management network.
NON_ADDRESSES = {'0.0.0.0', '255.255.255.0'}
IPV4 = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
LAB_RANGES = tuple(ipaddress.ip_network(value) for value in (
    '192.168.10.0/24', '192.168.20.0/24', '10.10.10.0/24',
    '192.168.150.0/24', '198.51.100.0/24', '127.0.0.0/8'))
# Synthetic management-network MACs used by the reference build (documented, not real).
SYNTHETIC_MAC = re.compile(r'\b52:54:00:ab:cd:[0-9a-f]{2}\b', re.I)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                   stderr=subprocess.DEVNULL)


def work_files():
    def walk(directory):
        for path in sorted(directory.iterdir()):
            name = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                yield name, None
            elif path.is_dir():
                if path.name not in LOCAL_ONLY:
                    yield from walk(path)
            elif path.is_file():
                yield name, path.read_bytes()
            else:
                yield name, None
    yield from walk(ROOT)


def committed_files(ref):
    tree = git('rev-parse', '--verify', '--end-of-options', ref + '^{tree}').strip().decode('ascii')
    for record in git('ls-tree', '-r', '-z', tree).split(b'\0'):
        if not record:
            continue
        info, name = record.split(b'\t', 1)
        mode, kind, oid = info.split()
        name = name.decode('utf-8')
        if mode not in (b'100644', b'100755') or kind != b'blob':
            yield name, None
        else:
            yield name, git('cat-file', 'blob', oid.decode('ascii'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-ref', help='Inspect committed blobs, for example HEAD')
    args = parser.parse_args()
    findings = 0
    seen = set()

    def fail(name, category):
        nonlocal findings
        findings += 1
        print(f'FAIL: {name}: {category}')

    try:
        entries = committed_files(args.git_ref) if args.git_ref else work_files()
        for name, data in entries:
            seen.add(name)
            if name not in ALLOWED:
                fail(name, 'file outside curated manifest')
            if data is None:
                fail(name, 'symlink or unsupported entry')
                continue
            if len(data) > 150_000 or b'\0' in data:
                fail(name, 'oversized or binary file')
                continue
            try:
                content = data.decode('utf-8')
            except UnicodeError:
                fail(name, 'non-UTF-8 file')
                continue
            content = SYNTHETIC_MAC.sub('SYNTHETIC-MAC', content)
            for category, pattern in PATTERNS.items():
                if re.search(pattern, content, re.I):
                    fail(name, category)
            for value in set(IPV4.findall(content)) - NON_ADDRESSES:
                try:
                    address = ipaddress.ip_address(value)
                except ValueError:
                    fail(name, 'invalid IPv4')
                    continue
                if not any(address in network for network in LAB_RANGES):
                    fail(name, 'IPv4 outside documented lab ranges')
        for name in sorted(ALLOWED - seen):
            fail(name, 'required curated file missing')
    except (OSError, ValueError, subprocess.CalledProcessError, UnicodeError):
        print('FAIL: file or Git enumeration failed')
        return 1
    print(f'Checked {len(seen)} files; findings: {findings}')
    return int(bool(findings))


if __name__ == '__main__':
    sys.exit(main())
