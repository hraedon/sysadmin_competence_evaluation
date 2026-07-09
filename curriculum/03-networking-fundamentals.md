---
domain: 3
id: networking-fundamentals
title: "Networking Fundamentals"
subtitle: "Not network engineering. The diagnostic baseline a sysadmin needs to not be helpless — and to hand off intelligently."
---

# Domain 3: Networking Fundamentals

*Not network engineering. The diagnostic baseline a sysadmin needs to not be helpless — and to hand off intelligently.*

## Why This Domain Is Scoped This Way

The failure mode this domain addresses is not ignorance of networking — it is false confidence. A candidate who passed Server+ knows the OSI layers, the cable categories, and can recite the default port numbers. What they often cannot do is look at a symptom and reason backward to a network hypothesis, run a targeted test, and either resolve it themselves or hand it off to a network team with specific, actionable evidence.

This domain deliberately excludes deep routing protocol knowledge, spanning tree configuration, QoS design, and other topics that belong to a network engineer role. The scope is: what does a sysadmin need to know to diagnose infrastructure problems that involve the network, and to communicate credibly with the people who own it?

*The handoff skill is underrated. A sysadmin who can say 'I've confirmed the issue is layer 3, it affects traffic from this subnet to this destination, traceroute drops at this hop, and it started after this change' is dramatically more useful to a network team than one who says 'the network seems slow.' That framing is itself a testable competency.*

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Network Literacy | Can read and describe a network diagram, a firewall rule set, a DHCP scope configuration, or a DNS zone. Can explain what each component does and what would break if it were absent or misconfigured — without being able to build or modify any of them. |
| Level 2 | Network Audit | Given a reported symptom, can identify which network component is likely implicated and what evidence would confirm or rule out that hypothesis. Can review a firewall rule set for obvious gaps, a DNS configuration for common misconfigurations, or a DHCP scope for exhaustion risk. |
| Level 3 | Network Commission | Can write a clear, complete request to a network team — specifying what is needed, what systems are affected, what behavior is expected vs. observed, and what has already been ruled out. Can evaluate whether a delivered change addresses the stated requirement. |
| Level 4 | Network Adaptation | Can make targeted, low-risk network changes within their authority: adding a DNS record, creating a DHCP reservation, adjusting a Windows Firewall rule, reading and interpreting a packet capture at the symptom level. Changes are documented and reversible. |

## Core Concepts

### DNS: The Most Common Culprit

DNS failures account for a disproportionate share of connectivity complaints. The diagnostic challenge is that DNS failures often present as application failures — 'the website is down,' 'I can't reach the file server,' 'email isn't sending' — without any indication that name resolution is involved.

- Resolution order — how a Windows client resolves a name: hosts file, DNS cache, configured DNS servers, in that order. The hosts file override is a common source of confusion in environments where it was used as a workaround and then forgotten.

- TTL and caching — why a DNS change propagates to some clients immediately and others take hours. The distinction between the TTL on the record and the cache on the client resolver.

- Split-horizon DNS — why internal and external resolution of the same name can return different results, and why this is intentional in most hybrid environments.

- Authoritative vs. recursive — the difference between a server that owns a zone and one that queries on behalf of clients. Why pointing a client at an authoritative-only server breaks everything silently.

- Common failure modes — wrong record type (A vs. CNAME in contexts where CNAME is prohibited), missing PTR records causing authentication delays, stale records pointing to retired systems, missing SRV records breaking AD-integrated services.

*The nslookup / Resolve-DnsName test is not sufficient. A record that resolves correctly from the admin's workstation may not resolve correctly from the affected system, due to different DNS server assignments, split-horizon configurations, or local cache state. Always test from the affected system or a system in the same network segment.*

### DHCP: Scope, Exhaustion, and Reservations

DHCP failures are less common than DNS failures but more disruptive when they occur, because a system without an IP address cannot communicate at all. The diagnostic challenge is that DHCP failure often presents as a complete connectivity outage indistinguishable from a cable or switch problem until you check the IP address on the affected system.

- Scope exhaustion — when a DHCP scope runs out of available addresses, new devices cannot obtain a lease. Symptoms appear as new devices failing to connect while existing devices (still within their lease period) continue to work fine. The scope size calculation should account for peak concurrent devices, not just registered devices.

- Reservation management — a DHCP reservation ties a specific MAC address to a specific IP address within the DHCP server's scope. The reservation does not remove the address from the pool unless the pool is sized to exclude it. Duplicate IP conflicts occur when a reservation is created for an address already assigned by another reservation or already statically configured.

- Lease duration tradeoffs — short leases (hours) mean address exhaustion is recovered quickly after devices leave but increase DHCP server load. Long leases (days) reduce load but can exhaust scopes when the device population turns over quickly, such as in conference rooms or guest networks.

- Rogue DHCP servers — a device accidentally running a DHCP server (a home router plugged into a network port, a VM with a misconfigured network adapter) can hand out incorrect gateway and DNS information to clients that happen to request from it first. Symptoms are inconsistent: some clients work, others cannot reach external resources or domain services.

### Routing and the Default Gateway

Most sysadmins will never configure a routing protocol. What they need to understand is how traffic gets from a source to a destination, what the default gateway's role is, and what the symptoms of a routing problem look like as distinct from a DNS or firewall problem.

- The default gateway is the exit point for traffic destined for networks the local host does not have a specific route to. A misconfigured default gateway causes all off-subnet traffic to fail while on-subnet traffic continues to work. This is a reliable diagnostic indicator.

- Subnet boundaries — traffic between two hosts on the same subnet does not go through a router. Traffic between hosts on different subnets always goes through a router, even if those subnets are in the same physical building or on the same switch. Misconfigured subnet masks cause hosts to misidentify whether a destination is local or routed.

- Static routes — when a specific route is needed that the default gateway does not cover. Common in multi-site environments where traffic to a remote subnet must go through a specific interface or next hop. A missing static route causes selective reachability failure: some destinations work, others do not, and the pattern corresponds to subnet boundaries.

- Traceroute as a handoff tool — traceroute (tracert on Windows) shows the path packets take to a destination and where they stop. A sysadmin does not need to understand what to do about a routing problem, but they should be able to run traceroute, read the output, and report accurately: 'Packets reach this hop successfully and fail at the next hop, which resolves to this hostname.'

### VLANs: What a Sysadmin Needs to Know

VLANs are a network engineering concern, but sysadmins encounter their effects constantly. A server placed in the wrong VLAN cannot reach the systems it depends on. A workstation on an isolated VLAN cannot authenticate against a domain controller. Understanding VLANs at the conceptual level is sufficient for diagnosis; configuration belongs to the network team.

- A VLAN is a logical network boundary. Traffic between VLANs must be routed, even if the physical devices are connected to the same switch. From the perspective of a host, being on a different VLAN is identical to being on a different physical network segment.

- VLAN membership is assigned at the switch port level (for wired connections) or at the wireless AP level (for SSIDs mapped to VLANs). A device cannot choose its own VLAN — it is assigned by the network infrastructure.

- The diagnostic indicator of a VLAN problem is selective reachability that correlates with network segments rather than with specific hosts or services. If a server can reach everything on one IP range but nothing on another, and the boundary corresponds to a VLAN boundary, the likely issue is either a missing inter-VLAN routing rule or the server being assigned to the wrong VLAN.

### Firewall Rule Logic

Firewall rules are directional and ordered. Both of these properties are consistently misunderstood by candidates who have memorized firewall concepts without applying them to real configurations.

- Directionality — a firewall rule permits or denies traffic in a specific direction. A rule that permits inbound TCP 443 does not permit outbound TCP 443. In host-based firewalls (Windows Firewall), inbound and outbound rules are managed separately. In network firewalls, traffic flow direction depends on the interface perspective.

- Rule ordering — most firewalls evaluate rules top-to-bottom and stop at the first match. A permissive rule above a restrictive rule makes the restrictive rule irrelevant for traffic that matches the permissive one. A common mistake is adding a specific allow rule after a broad deny rule, then wondering why the allow rule has no effect.

- Stateful inspection — most modern firewalls track connection state, which means a rule permitting outbound traffic implicitly permits the return traffic for established connections. Understanding this prevents both over-permissive rules (adding an explicit inbound rule for return traffic that stateful inspection already handles) and misdiagnosis (assuming a connection is failing due to firewall when the return traffic is actually being blocked by the source host's firewall).

- The implicit deny — most firewall rule sets end with an implicit deny-all. Traffic that does not match any explicit permit rule is dropped. The symptom is a connection that times out rather than being actively refused. Timeout (no response) vs. reset (active refusal) is a useful diagnostic signal for whether traffic is being dropped silently or rejected at the destination.

### The Diagnostic Escalation Framework

Because networking is typically owned by a different team, the sysadmin's role in network diagnosis is to gather enough evidence to either resolve the issue within their authority or hand it off with specificity. The following framework is not a troubleshooting checklist — it is a way of thinking about what information is needed before escalation adds value.

- Establish the scope — is this affecting one host, multiple hosts on the same segment, all hosts in a site, or all hosts across multiple sites? Scope narrows the hypothesis space dramatically.

- Establish the layer — can the affected host get a DHCP lease? Can it ping its default gateway? Can it resolve DNS? Can it reach the specific service? Each of these tests a different layer and rules out a different class of problem.

- Establish the boundary — is traffic failing to a specific destination, to a specific subnet, or to everything off-subnet? The boundary often reveals the failure point.

- Establish the change correlation — did anything change in the network environment at or before the time the problem started? A change window, a new device, a configuration push, or even a power event can all introduce network problems.

- Document before escalating — when handing off to a network team, lead with: affected scope, layer where failure occurs, boundary of the failure, and the change correlation. 'DNS resolution fails for all clients in VLAN 20, ping to the default gateway succeeds, ping to the DNS server fails, and this started after last night's switch firmware update' is a complete handoff. 'The network is down in building B' is not.

## Reasoning Framework: OSI as Binary Search, Not Taxonomy

How it is normally taught: the OSI model is presented as seven named layers with corresponding real-world protocols and technologies mapped to each. Candidates memorize the layer names, the order, and representative examples at each layer. Comprehension is tested by asking which layer a given protocol operates at.

What it is actually for: the OSI model is a fault isolation instrument. Its value is not in naming the layers — it is in providing a principled method for narrowing the hypothesis space when something is broken. Given a connectivity failure, you can systematically rule out classes of problems by testing at each layer: if Layer 1 is confirmed (cable is connected, link light is present), physical problems are eliminated. If Layer 2 is confirmed (frames are being received, ARP resolution works), data link problems are eliminated. Each confirmed layer eliminates a class of problems and moves the investigation upward. This is binary search applied to network diagnosis.

What misuse looks like: a candidate who has memorized the OSI model will, when faced with a connectivity complaint, either guess at a likely cause based on experience or ask a series of unordered questions that may or may not cover the relevant layers. They have a taxonomy but not a method. The taxonomy tells them what the layers are called. The method tells them which layer to test next and what a result at that layer implies about the layers above and below it.

*The practical application: when diagnosing any connectivity failure, work from the bottom up. Can the host obtain a physical link? Can it send and receive frames on the local segment? Can it reach its default gateway? Can it resolve names? Can it reach the specific service? Each question is a layer test. A failure at any layer tells you where to focus and what to ignore above that point.*

## Assessment Exercises

### [LITERACY] Where Does It Break?

*Candidate is given a network diagram showing a workstation, an access switch, a distribution switch, a router, and a DNS/domain controller. A user reports they cannot access a file share by name. Candidate must describe, in order, which components are involved in a successful connection and what each one's role is.*

**Watch for:** Candidates who skip the DNS resolution step and go directly to the file share. Candidates who cannot explain why a name resolution failure produces a different symptom than a routing failure.

### [AUDIT] The DNS Hunch

*A user reports that a specific internal application is unreachable. The candidate runs nslookup from their admin workstation and the name resolves correctly. Candidate must explain why this test may not be sufficient, what additional tests they would run, and from where.*

**Watch for:** Candidates who accept the nslookup result as definitive. The correct answer involves testing from the affected system, checking client DNS server assignment, checking local cache state, and considering split-horizon behavior.

### [AUDIT] Scope This Failure

*Candidate is given a ticket: 'Three users in conference room B cannot get on the network. Other users in the building are fine. The users were fine yesterday.' Candidate must identify the most likely failure hypothesis, the tests that would confirm it, and what they would check before calling the network team.*

**Watch for:** Jumping to switch or VLAN conclusions without ruling out DHCP exhaustion, a bad cable run, or a switch port that went down. Good candidates check the IP address the affected devices obtained (or failed to obtain) before any other test.

### [AUDIT] Read the Firewall

*Candidate is shown a simplified Windows Firewall rule set with an outbound allow for TCP 443 to Any, followed by a block rule for TCP 443 to a specific IP, followed by an allow for all established connections. An application cannot reach a specific HTTPS endpoint. Candidate must identify whether the firewall is the cause and explain their reasoning.*

**Watch for:** Candidates who miss the rule ordering issue (the broad allow above the specific block makes the block unreachable). Candidates who cannot explain stateful inspection and why return traffic is handled separately from the initial connection.

### [COMMISSION] Write the Escalation

*Following a scenario in which the candidate has diagnosed a likely inter-VLAN routing problem, they must write the escalation to the network team. The escalation must be specific enough that the network team can investigate without asking clarifying questions.*

**Watch for:** Escalations that describe symptoms without diagnostic evidence. Escalations that omit the change correlation. Escalations that ask the network team to 'look into it' rather than to verify a specific hypothesis. The exercise explicitly rewards candidates who can say 'I believe the issue is X, because Y and Z, and the change correlation is W' over candidates who document the symptom and stop.
