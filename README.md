# Homelab Network Lab — Virtualized Segmented Network with OPNsense + Active Directory

A production-style virtualized network build, designed from scratch as a lab:
an OPNsense firewall-router VM segments one home/lab network into three VLANs,
with a Windows Server Active Directory domain controller handling identity,
DNS, and DHCP on the server VLAN.

> **Lab, not a production deployment.** All addresses, hostnames, and settings
> here are design values for a home/lab build. No employer network, client
> network, or production system is represented in this repo.

**What this demonstrates:** network segmentation with VLANs (802.1Q), firewall
policy design (default-deny + documented inter-VLAN matrix), VLAN trunking on
a virtual switch, Windows Server AD DS / DNS / DHCP administration, OPNsense
configuration (interfaces, aliases, DHCP relay/static mappings), and a
step-by-step build runbook with a verification checklist.

```
                    [ ISP / building uplink ]   WAN — DHCP from upstream
                              │
                    ┌─────────┴─────────────┐
                    │   OPNsense VM         │  2 GB RAM, 2 vNIC
                    │   firewall / router   │  WAN + trunked LAN
                    │   gateways: .1 each   │
                    └─────────┬─────────────┘
                              │  802.1Q trunk (tags 10, 20, 30)
                    ┌─────────┴─────────────┐
                    │  vSwitch              │  Proxmox (VLAN-aware bridge)
                    │  (hypervisor host)    │  or ESXi (VLAN port groups)
                    └──┬─────────┬─────────┬┘
                       │         │         │
              VLAN 10  │  VLAN 20│         │ VLAN 30
           192.168.10/24 192.168.20/24   192.168.30/24
              MGMT/LAN   SERVERS        IOT-GUEST
                  │         │             │
        ┌─────────┘    ┌────┴──────────┐  └──┬─────────────┐
        │ admin PC     │ labdc01 (AD)  │  guest Wi-Fi /   │
        │ .10.50 (rsv) │ .20.10 static │  IoT devices     │
        └──────────────┴───────────────┘  (no RFC1918      │
                                            lateral access)
```

## Repo layout

| Path | Purpose |
|---|---|
| `docs/architecture.md` | Design decisions, topology, OPNsense vs pfSense, hardening notes |
| `docs/ip-vlan-plan.md` | Address plan: VLANs, subnets, gateways, DHCP ranges, key hosts |
| `docs/firewall-rule-matrix.md` | Firewall policy: source → dest → port → action → justification |
| `docs/build-runbook.md` | Step-by-step build: hypervisor → OPNsense → VLANs → DC → verification |
| `docs/interview-answers.md` | "How did you build this?" — talking points for interviews |
| `templates/opnsense-aliases.example.xml` | Sanitized OPNsense config snippet: firewall aliases (placeholders) |
| `templates/opnsense-dhcp-static.example.xml` | Sanitized OPNsense config snippet: DHCP static mappings with `__PLACEHOLDERS__` |
| `templates/opnsense-firewall-rules.example.txt` | Human-readable rule list to apply via the OPNsense UI (not a raw export) |
| `scripts/validate-address-plan.py` | Consistency-checks the IP/VLAN plan (overlaps, gateways, DHCP ranges) |
| `.gitignore` | Keeps live config exports, backups, and credentials out of the repo |

## Quick start

```bash
# 1. Sanity-check the addressing plan before you build anything
python3 scripts/validate-address-plan.py

# 2. Build the lab on a host (Proxmox VE or ESXi), following the runbook
#    - Hypervisor + VLAN-aware vSwitch      -> docs/build-runbook.md §1-2
#    - OPNsense VM install + VLAN setup    -> docs/build-runbook.md §3-4
#    - Windows Server DC (AD DS/DNS/DHCP)  -> docs/build-runbook.md §5-6
#    - Firewall policy from the matrix     -> docs/firewall-rule-matrix.md

# 3. Verify against the checklist at the end of the runbook
#    (inter-VLAN reachability, guest/IoT isolation, AD DNS resolution)
```

## Security notes

- Default posture is **deny**: WAN→LAN is denied by default, and VLAN 30
  (IoT/Guest) cannot initiate connections to any RFC 1918 address — it only
  gets internet egress. Every allowed flow is listed and justified in
  `docs/firewall-rule-matrix.md`.
- Templates are **sanitized examples**, not live exports: no real credentials,
  keys, MAC addresses, or public IPs appear anywhere in this repo. Live
  OPNsense config backups and AD exports are git-ignored.
- The management VLAN (10) is the only segment allowed to reach firewall and
  hypervisor admin interfaces, and the OPNsense GUI is not exposed on WAN.

## Validation

- Address-plan consistency: `scripts/validate-address-plan.py` checks for
  overlapping subnets, gateways outside their subnet, DHCP ranges that fall
  outside the subnet / collide with the gateway / overlap static hosts, and
  duplicate host addresses. Result in this sandbox: **all checks passed**
  (`python3 scripts/validate-address-plan.py`, exit 0).
- Markdown tables in `docs/` were reviewed for column alignment/readability.
- **Not validated in this sandbox:** the OPNsense install, VM builds, VLAN
  trunking, and AD promotion cannot run here — this workspace has no
  hypervisor. Those steps are design/runbook material and are only proven
  when built on a real host (Proxmox VE or ESXi) and checked against the
  verification checklist in `docs/build-runbook.md`. Nothing in this repo
  claims a live deployment result.
