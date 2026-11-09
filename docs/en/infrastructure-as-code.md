# Reproducible lab (infrastructure as code)

[Home](../../README.md) · **English** | [Русский](../ru/infrastructure-as-code.md)

## Status and honesty note

The files under [`infra/`](../../infra/) rebuild the lab from documentation. They are **not** the original change scripts (those remain private, see [security](security.md)) and they have **not** been run end to end on fresh guests. The numbers in [validation](validation.md) describe the original lab, not this code.

| Component | What was actually checked |
|---|---|
| libvirt network XML | `xmllint` and `virt-xml-validate` pass |
| `lab.sh` | `bash -n`; full `--dry-run` of `up` reviewed. No guest was created |
| Ansible | `--syntax-check`, `ansible-lint` and `yamllint` pass; templates rendered from the inventory |
| Firewall | Generated `rules.v4` (open and strict mode) accepted by `iptables-restore --test` and the nftables example by `nft -c`, both in an unprivileged network namespace |
| SSH hardening | Drop-in accepted by `sshd -t`; effective-config assertions checked against real `sshd -T` output; client probe tested against throwaway local `sshd` instances (see [ssh-hardening](ssh-hardening.md)) |
| `site.yml` and `verify.yml` on real guests | **Not run** |

Treat the first real run as a test of this code, expect small fixes, and read every task before running it.

## What it builds

Six Debian 13 guests (1 vCPU, 512 MiB by default) on five libvirt networks:

| Network | Mode | Used by |
|---|---|---|
| `lab-lan`, `lab-dmz`, `lab-wan`, `lab-isp` | Isolated L2 bridge, no host address, no DHCP | The four lab segments |
| `lab-mgmt` | NAT, `192.168.150.0/24`, static leases | Ansible access and one-time package installation |

Guest and host objects are named `lab-*` / `labbr-*`, and the management network uses its own range, so the build can coexist with an existing lab. The script skips anything that already exists and never modifies it.

## Quick start

Prerequisites: libvirt (`qemu:///system`), `virt-install`, `qemu-img`, your user in the `libvirt` group, `ansible-core` on the controller, and a Debian 13 *genericcloud* qcow2 image downloaded from `cloud.debian.org` with its checksum and signature verified.

```bash
sudo install -d -o "$USER" -g libvirt /var/lib/libvirt/images/qemu-kvm-lab
cp debian-13-genericcloud-amd64.qcow2 /var/lib/libvirt/images/qemu-kvm-lab/base.qcow2
export LAB_BASE_IMAGE=/var/lib/libvirt/images/qemu-kvm-lab/base.qcow2
export LAB_SSH_PUBKEY=~/.ssh/id_ed25519.pub     # a PUBLIC key file
infra/libvirt/lab.sh --dry-run up
infra/libvirt/lab.sh up
```

Wait for the guests to boot, then:

```bash
cd infra/ansible
ansible-playbook playbooks/site.yml             # bootstrap (packages), addressing, firewall, web, SSH hardening
ansible-playbook playbooks/verify.yml           # read-only traffic matrix
ansible-playbook playbooks/audit_ssh.yml        # read-only SSH audit
```

To remove the lab again, run `infra/libvirt/lab.sh destroy` from the repository root; it asks for confirmation and touches only `lab-*` objects.

## Design decisions and deviations from the original lab

- **Management NIC.** The original lab had none (guests were inspected through the QEMU guest agent). Ansible needs a path, so every guest gets `enp1s0` on `lab-mgmt`. This is a deliberate, documented deviation; it also gives the routers a place to allow SSH from without opening it to every segment.
- **No Internet inside the lab.** The management network is NAT only so that `bootstrap.yml` can install packages. It adds a *runtime-only* default route, installs everything (including packages for optional TLS and SSH hardening), and removes the route again. The static cloud-init configuration never contains a default route, so the ISP router keeps "no default route".
- **Interface names.** Names `enp2s0…` assume virtio NICs in creation order on a q35 guest. The `network` role fails with a clear message if one does not exist; override `lab_interfaces` in the inventory.
- **Routes.** The ISP router's static routes are written as ifupdown `post-up` lines instead of the original `lab-routes.service`. The effect is the same; the mechanism differs.
- **Firewall.** `lab-firewall.service` loads `/etc/iptables/rules.v4` before `network-pre.target`, and the edge router's interfaces carry a `pre-up` gate that refuses to start before it. Rules follow [architecture](architecture.md): FORWARD DROP; LAN→WAN DNS/HTTP/HTTPS/ICMP; LAN and WAN→DMZ TCP 80/443 to the web endpoint; WAN DNAT of the published address; LAN MASQUERADE; DMZ SNAT.
- **INPUT policy.** `edge_input_mode: open` (default) keeps the documented INPUT ACCEPT. `strict` sets default DROP, allows SSH only from the management network and the LAN (rate limited), and changes matrix check 11 from "open" to "blocked". Use `-e edge_input_mode=strict` and re-run `site.yml` and `verify.yml`. An equivalent native ruleset is in [`infra/examples/edge-router.nft`](../../infra/examples/edge-router.nft).
- **Web endpoints.** `lab-web.service` runs `python3 -m http.server` as `www-data` with `CAP_NET_BIND_SERVICE` only, `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp` and `PrivateDevices`, serving a root-owned read-only directory with an explicit `index.html` (no directory listing).

## Adding TLS (optional)

The documented lab serves plain HTTP. `web_tls_enabled: true` adds an HTTPS listener in front of the same content:

```bash
ansible-playbook playbooks/site.yml -e web_tls_enabled=true
```

`stunnel4` terminates TLS 1.2+ on port 443 and forwards to the local HTTP service; a self-signed ECDSA certificate is generated once on the guest. Self-signed is deliberate: the lab has no DNS and no public name, so no public CA can issue a certificate and clients must pin or trust it explicitly. The existing FORWARD and DNAT rules already allow port 443 to the web endpoint. To make the endpoint HTTPS-only, bind the plain listener to loopback (`web_bind: 127.0.0.1`, `web_port: 8080`). For anything beyond a lab, use an internal CA or ACME with a real name, short lifetimes and monitored renewal. This role has not been run on a guest.

## Known gaps

No off-host backup, no DNS, no IPv6 rules, no monitoring, no unattended-upgrade policy, and only TCP checks in `verify.yml`. These are listed deliberately; see also [security](security.md).
