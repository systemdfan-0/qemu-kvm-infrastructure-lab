# QEMU/KVM Infrastructure Lab — case study

[Home](../../README.md) · **English** | [Русский](../ru/portfolio-case.md)

## Problem and work

A personal six-VM Debian lab simulated LAN, DMZ, WAN and ISP networking. Configuration and service behavior needed to be established from evidence rather than inferred from VM names. Three powered-off auxiliary VMs were documented separately.

The initial DeepSeek-assisted audit and remediation replaced unsafe root HTTP processes with unprivileged systemd services and persisted NAT, firewall, forwarding, secondary addressing and ISP routes. Codex independently validated those changes, corrected early firewall startup with an ifupdown gate, made secondary addressing repeatable without hiding failures and assigned static web content to root while retaining an unprivileged read-only service.

Fresh configuration recovery copies were verified before reboot. All six main guests then passed individual reboot checks, followed by 33 successful network expectation checks. Verified paths include LAN HTTP access, WAN DNAT, LAN MASQUERADE and controlled inter-segment denials. Both web services passed restart, privilege and synthetic escape checks. Full details and untested scenarios are in [validation](validation.md).

This is AI-assisted learning work. It demonstrates Linux networking, QEMU/KVM and libvirt documentation, systemd service hardening, least privilege, recovery planning and careful separation of observations from assumptions. It is not commercial delivery or proof of production operations experience.

## Short portfolio description

QEMU/KVM Infrastructure Lab is a personal Linux networking project built around six Debian VMs and LAN/DMZ/WAN/ISP segments. It documents static routing, NAT and firewall behavior, safer systemd HTTP services, verified persistence after guest reboots and 33 successful network checks, with explicit security and recovery limitations.

## Next learning tasks (not implemented)

Define management-plane ACLs and an SSH authentication policy; add DNS/TLS if needed; design independent full-system backups and test restoration; expand IPv6 and alternative-path tests. These are future work, not delivered capabilities. The existing portfolio website was not modified.
