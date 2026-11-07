# Validation and reboot results

[Home](../../README.md) · **English** | [Русский](../ru/validation.md)

These results summarize the final authorized validation on 7 November 2026. No new live audit was performed when preparing this repository. Private final audit, test matrix, security, reboot and recovery reports take precedence over older inventory text. Raw evidence remains private, so this repository is a sanitized report rather than an independently executable evidence archive.

PASS means the observed result matched the expectation within the stated scope; an expected denial counts as PASS. NOT TESTED means absent or unexercised functionality. Network tests used bounded HTTP HEAD/GET, SSH banner/TCP and ICMP probes inside the lab. Successful SSH banners do not establish successful authentication.

## Reboot checks

| Order | Public role alias | Result |
|---|---|---|
| 1 | ISP router | PASS |
| 2 | Edge router | PASS |
| 3 | DMZ web endpoint | PASS |
| 4 | ISP client | PASS |
| 5 | LAN client A | PASS |
| 6 | LAN client B | PASS |

Each guest received one authorized reboot. Changed boot identifiers and return of QGA confirmed actual reboot; identifiers are omitted. IPv4 addresses/prefixes/interfaces, route destination/gateway/device, forwarding and required units were compared with the baseline. No manual emergency recovery was required. Both routers had forwarding enabled; the other four guests did not. The final network matrix ran after all six returned.

Required units returned; failed units were zero. Saved/runtime firewall rules matched and `iptables-restore --test` succeeded. Firewall completion preceded ifup/networking in the observed boot; this is startup-order evidence, not continuous packet-capture proof. Optional AF_VSOCK generator errors remained; see [security](security.md).

## Complete final network matrix: 33 PASS, 0 FAIL

Targets below use lab-private addresses and documentation-only WAN mapping. Role aliases are defined in [architecture](architecture.md).

| # | Flow / target | Observed result | Status |
|---|---|---|---|
| 1 | Edge router → 192.168.10.10:22 | SSH banner | PASS |
| 2 | Edge router → 192.168.10.11:22 | SSH banner | PASS |
| 3 | Edge router → 192.168.20.10:22 | SSH banner | PASS |
| 4 | Edge router → 198.51.100.2:22 | SSH banner | PASS |
| 5 | ISP router → 10.10.10.10:22 | SSH banner | PASS |
| 6 | ISP router → 10.10.10.10:ICMP | ICMP reply | PASS |
| 7 | ISP router → 10.10.10.10:80 | HTTP 200 | PASS |
| 8 | DMZ web endpoint → 192.168.10.10:22 | Expected timeout | PASS |
| 9 | DMZ web endpoint → 192.168.10.11:22 | Expected timeout | PASS |
| 10 | DMZ web endpoint → 10.10.10.10:80 | Expected HTTP connection error (URLError) | PASS |
| 11 | DMZ web endpoint → 192.168.20.1:22 | SSH banner | PASS |
| 12 | DMZ web endpoint → 10.10.10.10:ICMP | Expected no ICMP reply (exit 1) | PASS |
| 13 | DMZ web endpoint → 127.0.0.1:80 | HTTP 200 | PASS |
| 14 | ISP client → 198.51.100.10:80 | HTTP 200 | PASS |
| 15 | ISP client → 192.168.20.10:80 | HTTP 200 | PASS |
| 16 | ISP client → 192.168.10.10:22 | Expected timeout | PASS |
| 17 | ISP client → 192.168.10.11:22 | Expected timeout | PASS |
| 18 | ISP client → 198.51.100.10:22 | Expected timeout | PASS |
| 19 | ISP client → 192.168.20.10:22 | Expected timeout | PASS |
| 20 | ISP client → 10.10.10.1:22 | SSH banner | PASS |
| 21 | LAN client A → 192.168.20.10:80 | HTTP 200 | PASS |
| 22 | LAN client A → 10.10.10.10:80 | HTTP 200 | PASS |
| 23 | LAN client A → 198.51.100.10:80 | Expected HTTP connection error (URLError) | PASS |
| 24 | LAN client A → 192.168.10.11:22 | SSH banner | PASS |
| 25 | LAN client A → 192.168.10.1:22 | SSH banner | PASS |
| 26 | LAN client A → 192.168.20.10:22 | Expected timeout | PASS |
| 27 | LAN client A → 10.10.10.10:22 | Expected timeout | PASS |
| 28 | LAN client A → 198.51.100.2:ICMP | ICMP reply | PASS |
| 29 | LAN client B → 192.168.20.10:80 | HTTP 200 | PASS |
| 30 | LAN client B → 10.10.10.10:80 | HTTP 200 | PASS |
| 31 | LAN client B → 192.168.10.10:22 | SSH banner | PASS |
| 32 | LAN client B → 192.168.20.10:22 | Expected timeout | PASS |
| 33 | LAN client B → 10.10.10.10:22 | Expected timeout | PASS |

Positive controls confirmed listening SSH endpoints from allowed peers; the ISP router also reached ISP HTTP and ICMP. Negative results therefore were not inferred solely from absent listeners. Aggregate counter deltas during the final matrix were FORWARD DROP +23, MASQUERADE +3 and DNAT +3. These are snapshot deltas, not per-flow packet captures. The ISP HTTP endpoint observed the translated LAN source. Hairpin NAT is not configured; LAN uses private DMZ HTTP.

## Service hardening and recovery checks

Both web endpoints passed explicit restart and reboot checks: unprivileged runtime user, only `CAP_NET_BIND_SERVICE`, `NoNewPrivileges`, read-only mount and root-owned web directory/files (0755/0644). Three synthetic escape probes per endpoint returned 404 without disclosing a non-secret root canary; test artifacts were removed. Real credentials were not read or requested.

Fresh configuration archives for all six guests passed checksums, comparison and separate extraction. Exported-copy hashes matched. Rule restore validation and rollback-script syntax checks passed; a harmless timer probe passed on retry with explicit timer accuracy. An initial timing/tooling failure was not counted as a network PASS. Actual emergency rollback was not needed or executed.

## NOT TESTED / limits

| Scenario | Reason |
|---|---|
| Standalone outbound DMZ SNAT | Policy denies new DMZ → WAN; rule counter remained zero |
| HTTPS/TLS and DNS resolution | No TLS listener; no guest nameserver; IP-only design |
| SSH authentication | Transport/configuration only; passwords and keys untouched |
| Complete VM restore / emergency rollback | Configuration recovery checks only; no full image restore |
| All protocols / IPv6 / alternative host paths | Selected IPv4 paths only; host rules not independently validated |
| External network / Internet | Outside scope; ISP router has no default route |
| Host reboot / power-cycle / firewall-load failure | Not exercised; one guest reboot cycle only |
| Auxiliary VM live behavior | Three auxiliary guests remained off |

Configuration copies are on the same physical host and are not independent off-host backups. No RPO/RTO guarantee is established. Future updates, hotplug and storage failure scenarios remain untested. See [security and remaining risks](security.md).
