# SSH authentication policy and verification

[Home](../../README.md) · **English** | [Русский](../ru/ssh-hardening.md)

The original validation proved that SSH banners were reachable, not that authentication was safe ([validation](validation.md)). This page defines a policy, a checklist and tooling to close that gap. **Status:** the policy and tools were tested against throwaway local `sshd` instances only; they have not yet been applied to or run against the six lab guests.

## Policy

| Control | Setting | Reason |
|---|---|---|
| Password login | `PasswordAuthentication no`, `KbdInteractiveAuthentication no` | Removes online password guessing |
| Methods | `AuthenticationMethods publickey` | One explicit method |
| Root | `PermitRootLogin no` | Administration through a named account plus `sudo` |
| Accounts | `AllowUsers <admin account>` | Service accounts cannot log in |
| Brute force | `MaxAuthTries 3`, `LoginGraceTime 30`, `MaxStartups 10:30:60`, fail2ban (5 failures / 10 min → 1 h ban, nftables) | Slows scanners; management network is never banned |
| Surface | `X11Forwarding no`, `AllowAgentForwarding no`, `AllowTcpForwarding no`, `PermitTunnel no` | Not needed in the lab; enable per host if a jump host is required |
| Idle sessions | `ClientAliveInterval 300`, `ClientAliveCountMax 2` | Drops dead sessions |
| Reachability | Router `edge_input_mode: strict` | SSH only from management and LAN, rate limited, default DROP on INPUT |

The settings live in `/etc/ssh/sshd_config.d/00-lab-hardening.conf`. The `00-` prefix matters: `sshd` keeps the **first** value it reads, so a later drop-in (for example `50-cloud-init.conf` setting `PasswordAuthentication yes`) cannot override it. The role then asserts the **effective** configuration from `sshd -T`, so an override is detected, not assumed away.

## Apply

```bash
cd infra/ansible
ansible-playbook playbooks/ssh_hardening.yml      # also part of site.yml
```

Lock-out protection: the role aborts if an allowed account has no `authorized_keys`, validates the file with `sshd -t` before installing it, and only reloads (never restarts) the daemon, so existing sessions survive. Keep a second session open while you apply it to a machine you cannot reach physically.

## Verification checklist

1. `ansible-playbook playbooks/audit_ssh.yml` – every policy line reports PASS from the *effective* configuration; `ssh` and `fail2ban` are running.
2. From a client: `python3 scripts/ssh_check.py --user debian --identity ~/.ssh/id_ed25519 192.168.150.11 192.168.150.12 …`
   - banner present;
   - only `publickey` is advertised (no `password`, no `keyboard-interactive`);
   - root login with a valid key is refused;
   - normal key login works (positive control, so the negative results are meaningful).
3. Negative test of the ban: from a disposable client, fail authentication more than `f2b_maxretry` times, then check `fail2ban-client status sshd`. Do not do this from the Ansible controller; its network is on the ignore list.
4. Router exposure (strict mode): `verify.yml` check 11 must now report *blocked* from the DMZ.
5. Record the dates and results in [validation](validation.md) only after running them on the real lab.

`scripts/ssh_check.py` never sends a password: it runs `ssh` in `BatchMode`, which cannot prompt. It does not verify host keys during the probes, because they carry no secret; use your own `known_hosts` for real logins.

## What was actually tested here

- `sshd -t` accepts the generated drop-in.
- The assertion strings match real `sshd -T` output. This found a bug: current OpenSSH prints keys in CamelCase, older releases in lower case, so the comparison is case-insensitive.
- Against a hardened local `sshd` the probe reported only `publickey` and a successful key login; against a deliberately weak one it reported `FAIL` because `password` and `keyboard-interactive` were advertised. The root check is only meaningful against a real root-capable daemon, so it was not exercised here.

## Not covered

Key lifecycle and revocation, hardware-backed keys or SSH certificates, multi-factor authentication, bastion hosts, log shipping and alerting, and host-key pinning. They are sensible next steps and are not claimed.
