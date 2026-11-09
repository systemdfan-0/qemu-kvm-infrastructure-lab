#!/usr/bin/env python3
"""Black-box SSH authentication probe (client side, standard library only).

For every target it checks what an outside client can observe:

  1. TCP connect and SSH banner.
  2. Authentication methods advertised to an unauthenticated client. FAIL if
     "password" or "keyboard-interactive" is offered.
  3. (with --identity) root login with a valid key is refused.
  4. (with --identity) a normal user can log in with the key (positive control, so the
     negative results above are not caused by a broken connection).

No password is ever sent: ssh runs with BatchMode=yes, so it cannot prompt for one.
Host keys are NOT verified during checks 2-3 (the probe sends no secret); use your own
known_hosts for real logins. Exit status is 0 only if every check passed.

Usage:
  ssh_check.py [--user USER] [--identity KEYFILE] [--timeout SEC] HOST[:PORT] ...
"""
import argparse
import re
import socket
import subprocess
import sys

BASE = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'LogLevel=ERROR',
        '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'IdentityAgent=none', '-o', 'IdentitiesOnly=yes']
DENIED = re.compile(r'Permission denied \(([^)]*)\)')


def split_target(value):
    host, sep, port = value.rpartition(':')
    if sep and port.isdigit() and not host.endswith(':'):
        return host, int(port)
    return value, 22


def banner(host, port, timeout):
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            return sock.recv(128).decode('ascii', 'replace').strip()
    except OSError as exc:
        return 'ERROR: ' + exc.__class__.__name__


def ssh(host, port, user, timeout, identity=None, command=None):
    argv = BASE + ['-p', str(port), '-o', f'ConnectTimeout={timeout}']
    argv += ['-i', identity] if identity else ['-i', '/dev/null']
    argv += [f'{user}@{host}']
    if command:
        argv.append(command)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout * 3)
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    return proc.returncode, proc.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('targets', nargs='+', metavar='HOST[:PORT]')
    parser.add_argument('--user', default='debian', help='normal account for the probe')
    parser.add_argument('--identity', help='private key for checks 3-4 (never printed)')
    parser.add_argument('--timeout', type=int, default=8)
    args = parser.parse_args()

    failures = 0

    def report(target, name, ok, detail=''):
        nonlocal failures
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {target:<22} {name:<34} {detail}")

    for target in args.targets:
        host, port = split_target(target)
        text = banner(host, port, args.timeout)
        up = text.startswith('SSH-')
        report(target, 'banner', up, text)
        if not up:
            continue

        code, err = ssh(host, port, args.user, args.timeout)
        found = DENIED.search(err or '')
        if found is None:
            report(target, 'advertised auth methods', False, f'unexpected: {err[:60]!r}')
        else:
            methods = {m.strip() for m in found.group(1).split(',')}
            weak = sorted(methods & {'password', 'keyboard-interactive'})
            report(target, 'no password/kbd-interactive', not weak,
                   'offered: ' + ','.join(sorted(methods)))

        if args.identity:
            code, err = ssh(host, port, 'root', args.timeout, args.identity, 'true')
            report(target, 'root login with valid key refused', code not in (0, None),
                   'refused' if code not in (0, None) else 'ROOT LOGIN WORKS')
            code, err = ssh(host, port, args.user, args.timeout, args.identity, 'true')
            report(target, f'key login as {args.user} (control)', code == 0,
                   'ok' if code == 0 else (err or 'failed')[:60])

    print(f'\n{failures} check(s) failed' if failures else '\nAll checks passed')
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
