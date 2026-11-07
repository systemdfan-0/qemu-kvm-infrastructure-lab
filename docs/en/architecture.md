# Architecture and inventory

[Home](../../README.md) · **English** | [Русский](../ru/architecture.md)

Snapshot: 7 November 2026. All node labels below are public role aliases. They cannot be used as live libvirt domain names.

## Main lab: six Debian VMs

| Role alias | Interfaces / addresses | Purpose |
|---|---|---|
| Edge router | LAN `192.168.10.1/24`; DMZ `192.168.20.1/24`; WAN `198.51.100.1/30` and `198.51.100.10/30` | Routing, NAT, forwarding firewall |
| ISP router | WAN `198.51.100.2/30`; ISP `10.10.10.1/24` | Static ISP routing, no default route |
| LAN client A | `192.168.10.10/24` | Internal client |
| LAN client B | `192.168.10.11/24` | Internal client |
| DMZ web endpoint | `192.168.20.10/24` | Static HTTP test service |
| ISP client | `10.10.10.10/24` | External-side test client and HTTP endpoint |

Each main guest was inventoried with 1 vCPU and 512 MiB RAM. The main guests were running at the final validation; this is not a current status query.

## Auxiliary inventory: three VMs, outside the main lab

| Public role alias | Connection | Recorded state | Evidence scope |
|---|---|---|---|
| Auxiliary A | system libvirt, default NAT network | Off | Configuration only |
| Auxiliary B | system libvirt, default NAT network | Off | Configuration only |
| Auxiliary C | session libvirt, user-mode networking | Off | Configuration only |

Their live services and routing were not tested. They were not started or rebooted for the final validation.

## L2 transport and L3 routing

Six system libvirt networks were recorded: four lab segments, one default NAT network for auxiliary guests, and one unused DHCP-enabled segment. Guest addressing differs from host bridge addressing. The lab bridges carry L2 traffic; guest routers are the intended gateways. The host has no configured direct L3 route to the guest subnets, so guest inspection used QEMU guest agent over its management channel.

The default libvirt network has host-side NAT; NAT for the main lab is implemented inside the edge router. Isolated-mode libvirt networks alone do not prove exhaustive isolation through every host path. The unused segment has no attached VMs.

The [README diagram](../../README.md#architecture) and [Mermaid source](../../diagrams/network-topology.mmd) show the main lab. LAN clients use `192.168.10.1`; DMZ uses `192.168.20.1`; the ISP client uses `10.10.10.1` as gateway. The edge router's default next hop is represented as `198.51.100.2`. Static ISP routes allow return traffic and direct routed HTTP access to the private DMZ address.

## Firewall and address translation

| Mechanism | Documented behavior | Verification |
|---|---|---|
| FORWARD | DROP; established/related allowed | Rules and controlled traffic checks |
| LAN → WAN | DNS/HTTP/HTTPS/ICMP allowed by rules | Selected HTTP and ICMP tested; DNS/TLS unavailable |
| LAN/WAN → DMZ | TCP 80/443 to the DMZ endpoint allowed | HTTP tested; no TLS listener |
| LAN MASQUERADE | LAN source translated to router WAN address | Counters and source observed by ISP HTTP endpoint |
| WAN DNAT | `198.51.100.10` → `192.168.20.10`, WAN ingress only | ISP HTTP 200; LAN hairpin path unavailable |
| DMZ SNAT | `192.168.20.10` → `198.51.100.10` | Rule present; outbound flow NOT TESTED |

The existing DNAT rule is address-based; permitted forwarded ports are enforced by filtering. The ISP client also reaches private DMZ HTTP directly. Access is therefore not restricted exclusively to the translated address. New DMZ/ISP-to-LAN SSH attempts timed out; successful controls confirmed that the targets were listening. See the [complete matrix](validation.md).

## Persistence

The edge router restores `/etc/iptables/rules.v4` through `lab-firewall.service`, with early systemd ordering and an ifupdown pre-up gate. Static interfaces and sysctl preserve addresses and forwarding. A repeatable `ip addr replace` avoids hiding secondary-address failures. The ISP router restores routes through `lab-routes.service` and sysctl. Both HTTP endpoints use `lab-web.service`.

After individual guest reboots, saved/runtime rules matched (six filter rules and three NAT rules); required addresses, routes, forwarding and units returned. Observed firewall completion preceded ifup/networking. Host reboot, deliberate firewall-load failure and continuous packet capture throughout startup were not tested.

WAN addresses use TEST-NET `198.51.100.0/24`: primary transit `.0/30`, secondary `.8/30`. This is a documentation mapping, not deployable configuration. No VM identifiers, dynamic tap names or internal XML are included.
