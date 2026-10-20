# Firewall Rule Matrix (OPNsense)

Posture: **default deny** on every interface; rules below are applied top-down
on the relevant interface tab. `→` = initiated connections (stateful replies
are allowed automatically by the state table).

| # | Source → Dest | Port(s) | Action | Justification |
|---|---|---|---|---|
| 1 | WAN → any | any | **Deny (default)** | Internet must never initiate inbound connections to the lab; the OPNsense GUI is not exposed on WAN. |
| 2 | any → WAN (established) | any | Allow (stateful) | Return traffic for connections initiated from inside; required for updates and browsing. |
| 3 | VLAN10 (MGMT) → any | any | Allow | Admin segment: the only VLAN permitted to reach hypervisor/OPNsense management and to manage servers. |
| 4 | VLAN10 → SERVERS (192.168.20.0/24) | AD set¹ | Allow | Domain-joined workstations on MGMT need AD ports to the DC for logon, Group Policy, and DNS. |
| 5 | VLAN20 (SERVERS) → any | any | **Deny (default)** | Servers do not roam; they expose defined services only, and breaches here must not spread freely. |
| 6 | SERVERS → WAN | 80/443 | Allow | Patches, time sync (NTP over 123 optional), and Windows Update need outbound HTTPS only. |
| 7 | SERVERS → MGMT | any | **Deny** | Server breach must not pivot into the admin segment. |
| 8 | SERVERS → SERVERS (intra) | any | Allow | Backend traffic between lab servers (e.g. file share ↔ backup VM) stays inside the VLAN. |
| 9 | VLAN30 (IOT-GUEST) → 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12 | any | **Deny (alias: RFC1918_Networks)** | Guests and IoT devices cannot reach *any* internal address, including the DC and the admin VLAN. |
| 10 | VLAN30 → VLAN30 (gateway only) | 53, 80/443 (to 192.168.30.1 only) | Allow | Guests/IoT need DNS (OPNsense forwarder) and the captive-portal/admin UI none — gateway is resolver + egress only. |
| 11 | VLAN30 → WAN | 80/443 | Allow | Guest internet access (web). No SMB, no RDP, no arbitrary ports outward beyond what's listed. |
| 12 | MGMT → OPNsense (192.168.10.1) | 443, 22 | Allow | Web GUI + SSH management, admin VLAN only. |
| 13 | SERVERS → OPNsense (192.168.20.1) | 53 | Allow | Servers use OPNsense as fallback DNS for external names the DC doesn't resolve. |

¹ **AD port set** (VLAN10→DC 192.168.20.10): TCP/UDP 53 (DNS), TCP/UDP 88
(Kerberos), TCP/UDP 389 (LDAP), TCP 445 (SMB/Group Policy), TCP 135 (RPC
endpoint mapper), TCP 3268/3269 (Global Catalog), TCP/UDP 464 (Kerberos
change), UDP 123 (NTP), TCP 9389 (ADWS). In OPNsense this is one alias
(`AD_Domain_Ports`) rather than nine rules.

## Implementation notes

- Rule 9 uses a **firewall alias** (`RFC1918_Networks` containing
  `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) so the isolation rule
  survives even if subnets are renumbered — the template is in
  `templates/opnsense-aliases.example.xml`.
- Rule ordering matters: the RFC1918 block (9) sits **above** the guest
  WAN-allow (11); otherwise guests could reach internal addresses through
  the general allow. OPNsense evaluates rules first-match on the interface.
- Logging: rules 1, 5, 7, and 9 have logging enabled, so blocked attempts
  from guests/IoT and the WAN are visible in Firewall → Log Files → Live
  View — useful both for troubleshooting and for talking about the design
  in interviews.
- Anti-spoofing: OPNsense enables reverse-path filtering by default; each
  VLAN interface only accepts source addresses from its own subnet.
