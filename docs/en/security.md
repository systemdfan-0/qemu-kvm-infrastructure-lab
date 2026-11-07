# Security, limits and publication policy

[Home](../../README.md) · **English** | [Русский](../ru/security.md)

## Remediated findings

Two ad hoc Python HTTP servers previously ran as root from the privileged home directory and exposed directory listings containing sensitive filenames. Credential contents were not read. Initial remediation replaced them with `lab-web.service`, `www-data` and a dedicated `/srv/www/html` document root.

Final validation confirmed only `CAP_NET_BIND_SERVICE`, `NoNewPrivileges=yes`, `ProtectHome=yes`, `ProtectSystem=strict`, `PrivateTmp` and `PrivateDevices`. The static directory is root-owned 0755; files are root-owned 0644; the process sees read-only content. Restart/reboot and synthetic escape checks passed. These bounded probes do not establish immunity to every HTTP attack. Python `http.server` is a learning endpoint without TLS.

The firewall's late boot ordering was corrected to run before interface activation, with networking dependencies and an ifupdown gate. The secondary WAN address uses `ip addr replace` rather than suppressing errors. Existing filter/NAT policy and allowed ports were preserved.

## Remaining risks

| Area | Actual boundary |
|---|---|
| Router management | INPUT/OUTPUT ACCEPT; connected segments can reach router SSH |
| SSH | Password authentication for ordinary accounts remains enabled; root login is key-only; login/authentication was not tested |
| Forwarding isolation | Selected IPv4 paths tested; alternative host paths, all protocols and IPv6 not certified |
| DMZ access | ISP reaches both translated and private DMZ HTTP addresses |
| HTTP / DNS | No TLS; guest DNS absent; IP-only operation |
| Recovery | Verified configuration copies; no independent off-host full-system backup or restore drill |
| Startup | One guest reboot cycle; no host reboot or deliberate firewall-load failure test |
| Inventory hygiene | Shared guest hostname configuration and an unused network remain; actual names omitted |

Each guest retains one AF_VSOCK CID error and one optional SSH generator exit error per observed boot. No VSOCK device was configured; TCP SSH, QGA and required services worked, with zero failed units. The generator was not disabled to hide messages. Exact underlying timing was not established; VSOCK SSH is not claimed as functional. This was not a full CVE review, authentication assessment or adversarial security audit.

The repository describes a learning environment. It does not authorize exposing the running lab to the Internet and does not claim production readiness, commercial clients or certifications.

## Sanitization

Publication includes only curated Markdown, one Mermaid diagram, `.gitignore` and the local checker. Actual VM/domain names are replaced with role aliases. UUIDs, MACs, boot IDs, personal hostnames, home-network details, personal filesystem paths, internal XML, raw diagnostics, private privileged files, backups, disk images, credentials and screenshots are excluded. No operational audit/change/reboot scripts are distributed.

WAN mapping uses TEST-NET `198.51.100.0/24`: router `.1`, ISP router `.2`, published DMZ `.10`; transit ranges `.0/30` and `.8/30`. RFC1918 LAN/DMZ/ISP addresses are lab-local, not home-network addresses. Mapping affects documentation only.

Run `python3 scripts/check_public.py` for working-tree checks and `python3 scripts/check_public.py --git-ref HEAD` for committed blobs. The checker fails on unapproved files, symlinks, non-text data, identifier/key/credential patterns and IPv4 addresses outside the documented lab ranges. It prints filenames and categories without matched values. It uses no network, guest access or third-party dependencies. Pattern checks cannot replace reading every file or checking Git author metadata.

Before publication, review all content, links, Git status, staged names and author identity. Check committed blobs again after pushing and verify the remote tree/commit. `.gitignore` reduces accidental additions; it cannot sanitize already tracked content or history. Any future changes need the same review. GitHub visibility changes require the owner's separate approval after the private upload has been checked.
