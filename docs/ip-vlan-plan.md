# IP / VLAN Address Plan

All values are **design values** for a home network — no real
corporate or ISP network is represented. RFC 1918 private space is used
throughout; VLAN IDs 10/20/30 are the tagged VLANs on the OPNsense trunk.

## VLAN / subnet table

| VLAN ID | Name | Subnet | Gateway (OPNsense) | DHCP range | Purpose | Key hosts |
|---|---|---|---|---|---|---|
| 10 | MGMT/LAN | 192.168.10.0/24 | 192.168.10.1 | 192.168.10.100 – 192.168.10.199 | Admin laptops, hypervisor management, domain-joined workstations | 192.168.10.1 OPNsense gateway; 192.168.10.50 `admin-pc` (DHCP reservation); 192.168.10.2 hypervisor mgmt IP |
| 20 | SERVERS | 192.168.20.0/24 | 192.168.20.1 | 192.168.20.100 – 192.168.20.149 | Home servers (small scope — servers are static) | 192.168.20.1 OPNsense gateway; 192.168.20.10 `dc01.home.arpa` (AD DC, static); 192.168.20.11 `filesvr01` (placeholder, static) |
| 30 | IOT-GUEST | 192.168.30.0/24 | 192.168.30.1 | 192.168.30.100 – 192.168.30.250 | Guest Wi-Fi + IoT devices; fully isolated from internal subnets | 192.168.30.1 OPNsense gateway; all clients DHCP |

**VLAN 1 / untagged:** reserved for the hypervisor's native management on the
uplink; the OPNsense LAN vNIC carries only tagged traffic (10, 20, 30).
No untrusted device plugs into an untagged port.

## Conventions

- Gateway is always the first usable address (`.1`) on each VLAN, held by
  OPNsense — this keeps the rule of thumb consistent everywhere.
- Servers get static addresses **outside** the DHCP range (`.2`–`.99`
  on VLAN 20) so a DHCP server failure can't hand out a duplicate.
- Workstations stay on DHCP with reservations for machines the admin
  needs to reach by name (e.g. the admin PC).
- DHCP leases: 24 h on VLAN 10, 24 h on VLAN 20, 4 h on VLAN 30 (guest/IoT
  churn is high; short leases recycle addresses quickly).

## DNS design

- Domain: `home.arpa` (RFC 8375 — reserved for home networks, never a public
  zone). NetBIOS name: `HOME`.
- On VLAN 20, the DC (`dc01`) runs **AD-integrated DNS** and is the
  authoritative server for `home.arpa`.
- DHCP options per VLAN point clients at the right resolver:
  - VLAN 10/20 → 192.168.20.10 (the DC)
  - VLAN 30 → 192.168.30.1 (OPNsense DNS forwarder to upstream), so guests
    never touch AD DNS.
- The DC's DNS forwards non-authoritative queries to OPNsense (or a public
  resolver) via conditional-forwarders — the DC never gets the firewall
  bypassed.

## What changes for a production deployment

- Replace `home.arpa` with a registered domain you control if the network
  ever needs public DNS.
- Shrink DHCP scopes further and move every server to a reservation; document
  every static assignment in a change-controlled inventory.
