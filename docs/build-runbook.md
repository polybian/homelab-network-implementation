# Build Runbook — Homelab Network Lab

Prerequisites: a lab host with 2+ NICs, ≥16 GB RAM, ≥100 GB disk; Proxmox VE
8+ **or** ESXi 7/8 installer; OPNsense ISO; Windows Server 2022 (or 2025)
ISO + a valid evaluation or licensed key. All values below are lab design
values (see `ip-vlan-plan.md`).

## 1. Hypervisor install

1. Install Proxmox VE (or ESXi) on the host; give the management interface a
   static IP on your existing home network for now (it moves to VLAN 10 later).
2. **Proxmox:** make the LAN-side bridge VLAN-aware
   (`vmbr1`, VLAN aware = yes). **ESXi:** create a vSwitch on the LAN NIC
   with port groups `VLAN10`, `VLAN20`, `VLAN30` (VLAN IDs 10/20/30).
3. Enable hardware virtualization (VT-x/AMD-V) in BIOS; verify with
   `kvm-ok` (Proxmox).

## 2. OPNsense VM

1. Create the VM: 2 vCPU, 2 GB RAM, 20 GB disk, two virtio NICs
   (`em0` → WAN bridge/port group, `em1` → trunk bridge/port group).
2. Boot the OPNsense ISO, install to disk, reboot.
3. Assign interfaces at the console: WAN = `em0` (DHCP), LAN = `em1`
   (static for now — 192.168.10.1/24; VLANs come next).
4. Log in to the GUI at `https://192.168.10.1` from a machine on the
   trunk side; change the default `root`/`opnsense` password immediately
   and enable 2FA for the admin account.

## 3. VLANs + gateways on OPNsense

1. Interfaces → Other Types → **VLAN**: add three VLANs on parent `em1`
   with tags 10, 20, 30.
2. Interfaces → **Assignments**: assign each as `OPT1/OPT2/OPT3`, enable
   them, name them `MGMT_LAN`, `SERVERS`, `IOT_GUEST`, set static IPv4:
   `.10.1/24`, `.20.1/24`, `.30.1/24`.
3. Services → DHCPv4: enable on each VLAN with the ranges from
   `ip-vlan-plan.md` (VLAN 30 only, if DHCP lives on the DC for 10/20 —
   see §5; at minimum configure all three so the network works before AD).
4. **Verify:** from the OPNsense console, `ping` each gateway IP; from a
   test VM on each port group, confirm DHCP lease + gateway ping.

## 4. Firewall policy

1. Firewall → Aliases: create `RFC1918_Networks` (10.0.0.0/8,
   172.16.0.0/12, 192.168.0.0/16) and `AD_Domain_Ports` (the port set in
   the matrix) — see `templates/opnsense-aliases.example.xml`.
2. Apply the rules from `docs/firewall-rule-matrix.md` per interface tab,
   **in order** (deny-before-allow for the guest VLAN). Enable logging on
   the block rules.
3. Confirm the anti-lockout behavior: you must still reach the GUI from
   VLAN 10 after applying. Keep a console session open while editing rules.
4. **Verify:** from a VLAN 30 client, `ping 192.168.20.10` must fail and
   `curl https://example.com` must succeed; from VLAN 10, RDP/SSH to
   192.168.20.10 must succeed.

## 5. Windows Server — AD DS install

1. Create the VM on the SERVERS port group: 2 vCPU, 4 GB RAM, 60 GB disk;
   static IP 192.168.20.10/24, gateway 192.168.20.1, DNS 127.0.0.1 (self
   after promotion; temporarily use 192.168.20.1).
2. Install Windows Server; rename computer to `labdc01`; set the static IP.
3. Server Manager → Add Roles: **AD DS, DNS Server, DHCP Server**.
4. Promote to domain controller: new forest, root domain `lab.local`
   (NetBIOS `LAB`); set DSRM password; let DNS install as AD-integrated.
5. Configure DHCP scopes per `ip-vlan-plan.md` (VLAN 10: 192.168.10.100–199;
   VLAN 20: 192.168.20.100–149), with option 006 (DNS) = 192.168.20.10 and
   option 015 (DNS domain) = `lab.local`; enable DNS dynamic updates.
6. If DHCP stays on OPNsense instead: set OPNsense DHCP option 006 to
   192.168.20.10 and note that client DNS records won't self-register —
   the documented trade-off in `architecture.md`.

## 6. Join a client + Group Policy smoke test

1. Join a VLAN 10 VM to `lab.local`; confirm logon with a domain account.
2. `nslookup labdc01.lab.local` must resolve to 192.168.20.10 from VLAN 10.
3. Create a test GPO (e.g. a desktop wallpaper or a mapped drive) and
   confirm it applies with `gpresult /r`.

## 7. Verification checklist

- [ ] Each VLAN's DHCP hands out addresses from the planned range
- [ ] VLAN 30 client: internet works, all RFC 1918 destinations unreachable
- [ ] VLAN 10 admin PC: reaches OPNsense GUI, SSH to hypervisor, RDP to DC
- [ ] SERVERS → MGMT initiation is blocked (e.g. ping/DC-initiated SMB fails)
- [ ] WAN → any inbound connection is blocked (port-scan the WAN IP from outside)
- [ ] Domain join + logon + GPO application all succeed from VLAN 10
- [ ] Blocked attempts appear in OPNsense Firewall → Log Files (Live View)
- [ ] Config backup exported after final rule set (stored offline, git-ignored)
