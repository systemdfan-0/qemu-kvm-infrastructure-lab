# Reproducible lab (infrastructure as code)

Reference implementation that rebuilds the lab described in the top-level
[README](../README.md) from scratch. It was written **from the published documentation**,
not extracted from the original lab, and has not yet been run end to end on fresh guests.
Read [docs/en/infrastructure-as-code.md](../docs/en/infrastructure-as-code.md) for the
status, design decisions and deviations before using it.

| Path | Purpose |
|---|---|
| `libvirt/networks/*.xml` | Five libvirt networks: four isolated L2 segments and one management network |
| `libvirt/lab.sh` | Creates networks and six Debian 13 guests (`--dry-run` supported); touches only `lab-*` objects |
| `ansible/` | Roles for packages, static addressing, edge firewall, web endpoints, optional TLS, SSH hardening |
| `ansible/playbooks/verify.yml` | Read-only traffic matrix (TCP subset of the documented 33 checks) |
| `ansible/playbooks/audit_ssh.yml` | Read-only audit of the effective SSH configuration |
| `examples/edge-router.nft` | Native nftables equivalent of the edge-router policy |

Quick start (see the documentation page for prerequisites):

```bash
infra/libvirt/lab.sh --dry-run up      # prints what would be created
infra/libvirt/lab.sh up
cd infra/ansible
ansible-playbook playbooks/site.yml
ansible-playbook playbooks/verify.yml
```
