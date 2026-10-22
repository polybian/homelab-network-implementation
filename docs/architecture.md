# Architecture & Design Decisions

## Topology

- **Host:** one hypervisor (Proxmox VE or ESXi) on a dedicated machine with at
  least 2 NICs — one for WAN uplink, one for the trunked LAN side.
- **OPNsense VM** (primary firewall-router): 2 vNICs — `em0` = WAN (DHCP
  from the upstream modem/router), `em1` = LAN carrying 802.1Q-tagged
  VLANs 10/20/30. OPNsense holds the `.1` gateway on each VLAN and performs
  inter-VLAN routing; the firewall matrix decides what crosses.
- **Windows Server VM** on VLAN 20, static `192.168.20.10`, promoted to a
  domain controller for `home.arpa`: AD DS + DNS + DHCP roles (design
  choice below).
- **vSwitch:** Proxmox — one VLAN-aware bridge; OPNsense tags on the guest
  side. ESXi — port groups with VLAN IDs 10/20/30 on the trunked vSwitch,
  each VM attached to its port group.

## Why OPNsense over pfSense

Both are BSD-based firewall distributions and both would work. I picked
OPNsense as primary because:

- **Release cadence:** OPNsense ships smaller, more frequent updates; the
  project has a strong security-update track record.
- **UI/API:** the MVC/Phalcon-based UI is cleaner for firewall-rule review,
  and the REST API makes rule/alias management scriptable.
- **WireGuard:** first-class WireGuard support for a future remote-access
  extension (this build pairs naturally with a VPN server implementation).
- **Licensing clarity:** pfSense Plus branding/trademark friction on
  non-Netgate hardware is a distraction for a home build; OPNsense avoids it.

pfSense is documented in the runbook as the drop-in alternative — the VLAN,
firewall, and AD designs are identical; only the UI steps differ.

## Why one router does everything

OPNsense is the default gateway for all three VLANs (router-on-a-stick via
the tagged trunk) instead of adding a layer-3 switch. In a home network this is the
right call: one policy point, one log source, no ACL mismatch between a
switch and a firewall. At scale you'd move routing to a L3 switch and keep
the firewall at the perimeter.

## Why AD DS + DNS + DHCP on one DC

A single Windows Server VM holds all three roles — standard for a small
home/single-domain build:

- **AD DS:** identity for the network (users, groups, Group Policy). Forest
  functional level: highest the installed Windows Server supports.
- **AD-integrated DNS:** zone replication rides AD replication, and secure
  dynamic updates let domain members self-register — one less service to
  keep consistent.
- **DHCP on the DC** (not OPNsense) for VLANs 10/20, because DHCP/DNS
  dynamic-update integration (option 81) keeps forward/reverse records
  accurate when DHCP hands out names. OPNsense still runs DHCP on VLAN 30
  (guest/IoT have no business touching AD services), and provides the
  fallback DNS forwarder on every gateway.

Noted alternative: host DHCP on OPNsense for all VLANs and delegate only
DNS to AD — simpler for the firewall admin, but loses automatic DNS
registration of DHCP clients.

## Hardening notes

- **Default deny everywhere** (see the firewall matrix): WAN→LAN denied,
  SERVERS→MGMT denied, and VLAN 30 blocked from all RFC 1918 space.
- **Management plane isolation:** OPNsense GUI/SSH and the hypervisor
  console are reachable only from VLAN 10; anti-lockout rules stay at the
  top of the MGMT interface tab.
- **OPNsense system hardening:** disable password SSH (keys only), enable
  2FA on the admin GUI account, turn on automatic security updates,
  and keep a versioned config backup before every rule change
  (Diagnostics → Backup & Restore; exports are git-ignored).
- **DC hardening:** rename the local Administrator account, use LAPS-style
  unique local admin passwords on joined machines, keep the DC patched and
  never browse the web from it, enable Windows Firewall domain profile
  (allow only the AD port set from the firewall matrix).
- **Logging:** OPNsense logs blocked inter-VLAN attempts (guest/IoT
  probing) and outbound filter hits; forward syslogs to a collector so a
  reboot doesn't lose the evidence. On the DC, enable "Audit logon events"
  and DNS analytic logging for a troubleshooting trail.
