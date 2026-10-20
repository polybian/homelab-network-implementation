#!/usr/bin/env python3
"""validate-address-plan.py — consistency-check the Homelab IP/VLAN plan.

Mirrors docs/ip-vlan-plan.md. Exits non-zero and prints FAIL lines if:
  - any two subnets overlap
  - a gateway is outside its subnet, is not the first usable address,
    or collides with a static host / DHCP pool
  - a DHCP range falls outside its subnet, is reversed, or overlaps
    a static host or the gateway
  - a static host address is outside its subnet or duplicated
Run: python3 scripts/validate-address-plan.py
"""
from ipaddress import ip_address, ip_network

PLAN = [
    {
        "vlan": 10, "name": "MGMT/LAN",
        "subnet": "192.168.10.0/24", "gateway": "192.168.10.1",
        "dhcp": ("192.168.10.100", "192.168.10.199"),
        "static_hosts": ["192.168.10.1", "192.168.10.2", "192.168.10.50"],
    },
    {
        "vlan": 20, "name": "SERVERS",
        "subnet": "192.168.20.0/24", "gateway": "192.168.20.1",
        "dhcp": ("192.168.20.100", "192.168.20.149"),
        "static_hosts": ["192.168.20.1", "192.168.20.10", "192.168.20.11"],
    },
    {
        "vlan": 30, "name": "IOT-GUEST",
        "subnet": "192.168.30.0/24", "gateway": "192.168.30.1",
        "dhcp": ("192.168.30.100", "192.168.30.250"),
        "static_hosts": ["192.168.30.1"],
    },
]

errors = []

# 1. Subnet overlaps
networks = [(v["vlan"], ip_network(v["subnet"])) for v in PLAN]
for i, (vlan_a, net_a) in enumerate(networks):
    for vlan_b, net_b in networks[i + 1:]:
        if net_a.overlaps(net_b):
            errors.append(f"VLAN {vlan_a} subnet {net_a} overlaps VLAN {vlan_b} subnet {net_b}")

seen_hosts = {}
for v in PLAN:
    net = ip_network(v["subnet"])
    gw = ip_address(v["gateway"])
    lo, hi = ip_address(v["dhcp"][0]), ip_address(v["dhcp"][1])

    # 2. Gateway sanity
    if gw not in net:
        errors.append(f"VLAN {v['vlan']}: gateway {gw} not in {net}")
    if gw != net.network_address + 1:
        errors.append(f"VLAN {v['vlan']}: gateway {gw} is not first usable ({net.network_address + 1})")
    if gw in net and lo <= gw <= hi:
        errors.append(f"VLAN {v['vlan']}: gateway {gw} inside DHCP range")

    # 3. DHCP range sanity
    if lo > hi:
        errors.append(f"VLAN {v['vlan']}: DHCP range reversed ({lo} > {hi})")
    for addr, label in ((lo, "DHCP start"), (hi, "DHCP end")):
        if addr not in net or addr in (net.network_address, net.broadcast_address):
            errors.append(f"VLAN {v['vlan']}: {label} {addr} not a usable host address in {net}")
    if lo <= net.network_address or hi >= net.broadcast_address:
        errors.append(f"VLAN {v['vlan']}: DHCP range touches network/broadcast address")

    # 4. Static hosts
    for host in v["static_hosts"]:
        addr = ip_address(host)
        if addr not in net:
            errors.append(f"VLAN {v['vlan']}: static host {addr} not in {net}")
        if addr != gw and lo <= addr <= hi:
            errors.append(f"VLAN {v['vlan']}: static host {addr} inside DHCP pool {lo}-{hi}")
        if addr in seen_hosts:
            errors.append(f"duplicate host address {addr} (VLAN {seen_hosts[addr]} and VLAN {v['vlan']})")
        seen_hosts[addr] = v["vlan"]

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    raise SystemExit(1)

print(f"OK: {len(PLAN)} VLANs checked - no overlapping subnets, gateways valid, "
      f"DHCP ranges sane, {len(seen_hosts)} static hosts unique and outside DHCP pools.")
