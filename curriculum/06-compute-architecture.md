---
domain: 6
id: compute-architecture
title: "Compute Architecture"
subtitle: "From bare metal to orchestration — what each abstraction layer adds, costs, and hides"
---

# Domain 6: Compute Architecture

*From bare metal to orchestration — what each abstraction layer adds, costs, and hides*

## Purpose and Calibration

This domain covers more ground with more variation in required depth than any other in the framework. A sysadmin managing a Kubernetes cluster at a software company needs genuine depth in container orchestration. A sysadmin managing three VMs on a single Hyper-V host needs awareness, not expertise. The domain's goal is calibrated awareness across the full compute stack — enough conceptual framework that a candidate encountering any point in the stack understands what they are looking at, knows what questions to ask, and recognizes when they are out of their depth and need to find someone who is not.

That is a different goal than the earlier domains, most of which target operational competence within a defined scope. This domain is partly doing that for the layers where depth is universally required — VM management, basic container operations — and partly providing the orientation layer that makes depth achievable when it is needed.

*The security argument that runs through this entire domain: each layer transition in the compute stack trades isolation for efficiency. Isolation is the fundamental security primitive. Every virtualization and containerization technology is a controlled reduction of isolation in service of better resource utilization, and every such technology has a corresponding class of vulnerabilities whose blast radius is determined by how much isolation was traded away.*

## Reasoning Framework: Abstraction Layers Add Value and Hide Reality

How it is normally taught: compute technologies are presented as a progression of improvements — bare metal was the old way, VMs are better, containers are better still, Kubernetes is the modern approach. The implicit model is that each layer supersedes the previous one.

What it is actually for: each layer in the compute stack solves a specific problem and creates new ones. Hypervisors add hardware independence and resource pooling and introduce a new administrative plane that is a high-value attack target. Containers add deployment density and environment consistency and introduce shared kernel risk and supply chain complexity. Orchestration adds automated scheduling and self-healing and introduces a complex control plane and a new abstraction of 'where is this running' that makes debugging harder. Each layer is a tradeoff, not an upgrade.

What misuse looks like: treating the highest layer as universally appropriate. Running Kubernetes because it is modern. Containerizing workloads that have no meaningful benefit from containerization. The more consequential misuse is not understanding what each layer hides — the physical properties that an abstraction layer conceals resurface under failure conditions, under load, or under security compromise in ways that are only comprehensible if the underlying layer is understood.

The specific practitioner scenario: a candidate is asked to modernize a small organization's infrastructure. They recommend migrating three VMs from an on-premises Hyper-V host to containers orchestrated with Kubernetes, because containers are the modern approach. The workloads are a legacy .NET application with local file dependencies, a database server, and a file share. None of these are good container candidates. The .NET application requires refactoring to remove local state. The database server trades the predictable resource allocation of a VM for the complexity of persistent volumes in Kubernetes. The file share has no meaningful benefit from containerization at all. The recommendation adds a Kubernetes control plane, etcd, a CNI plugin, an ingress controller, persistent volume provisioning, and the operational overhead of maintaining all of it — in exchange for no concrete improvement in availability, performance, or deployment velocity. The candidate who makes this recommendation has learned the upgrade narrative rather than the tradeoff reasoning. The candidate who asks 'what does containerization actually buy for each of these specific workloads' and arrives at 'nothing, or less than the overhead costs' has understood the framework.

## Bare Metal: The Foundation

Bare metal is the physical machine running the operating system directly, with full access to hardware resources and no abstraction overhead. Understanding bare metal is not about preferring it to virtualization — it is about having a reference point for the properties that each abstraction layer modifies.

- Failure domain: the physical machine. A hardware failure affects only what runs on that machine. The blast radius of any single failure is bounded by what the physical host contains.

- Operational responsibility: total. Firmware, hardware, OS, and application are all the operator's concern. Nothing is abstracted away.

- Resource behavior: predictable. CPU cycles, memory access, storage I/O, and network bandwidth behave according to the hardware specification. There is no hypervisor tax, no contention with other tenants, no abstraction layer that might behave unexpectedly under load.

- Security isolation: maximum. The workload shares no software layer with any other workload. A compromise of the workload does not provide a direct path to other workloads. This is the isolation baseline — every layer above bare metal trades some portion of this isolation for the efficiency gains that layer provides.

Bare metal is correct for: workloads with extreme performance requirements (high-frequency trading, real-time signal processing), workloads with hardware dependencies that cannot be virtualized (GPU passthrough for production inference, specific network card features), and workloads where isolation is a hard requirement (regulatory, high-security, or trust boundary reasons). For everything else, the operational flexibility of virtualization justifies its costs.

## Hypervisors and the VM Model

### What Virtualization Adds and What It Costs

A Type 1 hypervisor (ESXi, Hyper-V, KVM) runs directly on the hardware and presents virtual machines as isolated compute environments. The value proposition is consolidation: multiple independent workloads run on a single physical host with hardware resource pooling, live migration for availability, and snapshot capabilities for rapid state capture.

- The consolidation security tradeoff: a single host compromise gives an attacker access to every VM running on it. Twenty servers consolidated onto two hypervisor hosts has made a sensible utilization decision and an often-unexamined blast radius decision. The failure domain has expanded from the physical machine to the virtualized estate on that host. This is the isolation-for-efficiency tradeoff made concrete: the efficiency gain is real (consolidation ratio), the isolation reduction is real (a single host failure now has a blast radius proportional to consolidation), and both should be part of the decision.

- The administrative plane as a high-value target: the vCenter, Hyper-V Manager, or equivalent that controls all VMs on all hosts is a single credential target whose compromise radius is the entire virtualized estate. Domain admin access to a vCenter or SCVMM is categorically different from domain admin access to a single member server. The tiering model from Domain 2 applies explicitly — the hypervisor management infrastructure belongs on a separate trust tier from the VMs it manages.

- Live migration and workload behavior: live migration moves a running VM from one host to another without downtime. From the application's perspective, memory contents are transferred while the VM continues running. Applications that assume persistent local state — certain database configurations, in-memory caches with local affinity — can behave unexpectedly after live migration. Understanding that live migration happens transparently, including during host maintenance, is necessary for debugging intermittent application behavior.

### Snapshot Behavior: The On-Premises Model Does Not Map to Cloud

On every mainstream on-premises hypervisor, a snapshot is a mechanism for reverting to a prior state. Take a snapshot before a risky change, verify the change worked, and delete the snapshot — or revert to it if the change failed. This is one of the most operationally useful features in virtualization and one that sysadmins who learn on-premises naturally rely on.

In Azure, a snapshot of a managed disk is an incremental backup artifact used for disk restoration, not a live state that can be reverted to while the VM continues running. The operation that Azure calls 'create snapshot' produces a point-in-time copy that can be used to restore a disk — a different operation from reverting to a running checkpoint. The VMware snapshot chain mechanism, the Hyper-V checkpoint mechanism, and the Azure snapshot mechanism use the same word for substantially different operations.

The broader pattern: every on-premises compute concept has a cloud equivalent that is approximately similar and specifically different in ways that matter under failure conditions. The candidate who carries the on-premises mental model without adjustment will be surprised at exactly the wrong moment — during an incident when they need to revert to a known-good state and discover the operation they expected does not exist.

## Containers: Environment Consistency at the Cost of Isolation

### What Containers Are and Are Not

A container is a process (or set of processes) running on a host OS with namespacing and cgroups providing the appearance of isolation. The container shares the host kernel. This is the fundamental difference from a VM: a VM has its own kernel, a container shares the host's. The implications flow from this:

- A container escape vulnerability — a bug that allows code running inside a container to break out and interact with the host — affects every container on the host simultaneously. The blast radius of a kernel vulnerability in a containerized environment is every container sharing that kernel. This is the specific isolation reduction containers make relative to VMs: a VM has its own kernel boundary, a container does not. The efficiency gained (deployment density, faster startup, smaller image size) comes from removing that boundary. The security cost is that every container on the host now shares the same kernel attack surface.

- Container root often maps closely to host root. By default, many container workloads run as root inside the container, and the mapping between container root and host root is closer than most operators realize. Running containers as non-root and using user namespace remapping are meaningful security controls that are not universally applied.

- The shared kernel means that kernel-level system calls from any container are processed by the host kernel. Workloads that need specific kernel features — some network monitoring tools, certain security software — may conflict across containers sharing a host. Workloads with specific kernel version requirements may not function correctly on a host with a different kernel version than they were developed against.

### The Supply Chain Problem

A container image is not just your application. It is your application plus everything in the base image plus everything your application's dependencies include plus everything their dependencies include. The dependency chain is frequently deep, often not audited, and automatically updated in ways that introduce new packages without operator review.

The package ecosystem that underlies most container images is broadly unregulated. The npm left-pad incident — where the removal of an 11-line package broke thousands of builds — illustrated how a dependency chain can make large portions of the software ecosystem dependent on unreviewed, unvetted packages maintained by individuals with no contractual obligation to anyone. The same ecosystem is now experiencing a newer attack vector: AI assistants hallucinate package names, attackers register those names in advance or immediately after, and organizations that install AI-recommended packages without verification install malware distributed through legitimate-looking package registry entries.

A Software Bill of Materials (SBOM) is the organized response to this risk: a complete inventory of every software component in a container image or application, their versions, and their provenance. SBOMs enable systematic checking of components against known vulnerability databases, auditing of dependency chains for unvetted packages, and detection of unexpected changes between builds. In practice, SBOMs are currently better as a conceptual framework than as an implemented operational control in most organizations — generating them is feasible, maintaining them as dependencies change and acting on what they reveal requires tooling and process maturity that most organizations are still developing.

*The minimum awareness for any sysadmin working with containerized workloads: the container image you are running contains software you did not write, did not review, and may not be aware of. Understanding the image build pipeline — what base image it uses, where packages come from, how frequently it is rebuilt against updated base images — is a prerequisite for making any meaningful security assessment of a containerized workload.*

### The VM-as-Special Versus Pod-as-Cattle Mindset Shift

The operational reflex that develops through years of VM management is: a system that is behaving unexpectedly gets investigated. You SSH into it, you look at logs, you understand what is wrong, you fix it in place. VMs are special. They have names, histories, accumulated state, and ongoing relationships with the operator who maintains them.

The operational model that containers are designed around is different: a container that is behaving unexpectedly gets killed and replaced. The replacement starts from a known-good image with a clean state. If the replacement also behaves unexpectedly, then you investigate. Containers are not special. They are instances of an image, interchangeable and disposable.

The failure modes of carrying the wrong model into the wrong environment:

- VM reflex applied to containers: SSHing into a running container to debug it, making changes inside the running container, and wondering why they disappear on restart. The container filesystem is ephemeral. Changes made to a running container do not persist. The fix that worked in the running container will not survive the next restart. The correct response is to fix the image and redeploy, not to fix the running instance.

- Container reflex applied to VMs: deleting and recreating a VM when something is wrong rather than diagnosing, because 'that is how you fix containers.' VMs accumulate state that matters — log files, application data that was not externalized, local configurations that were not captured in automation. A VM recreated from an image loses whatever state it had accumulated since the image was created. 'Delete it and see if it comes back healthy' is appropriate for pods and dangerous for VMs.

## Orchestration: Kubernetes and What It Actually Solves

### The Problem Kubernetes Addresses

Kubernetes solves a real problem: running many containerized workloads across many nodes with automated scheduling, self-healing, rolling deployments, and horizontal scaling. At the scale and organizational maturity where this problem genuinely exists, Kubernetes addresses it well. The control plane handles failure detection and workload rescheduling. Deployments describe desired state and Kubernetes works to maintain it. Horizontal pod autoscaling responds to load. These are genuinely valuable capabilities for organizations that have them as requirements.

### The Organizational Fit Question

It is the position of the authors of this framework that Kubernetes is employed primarily in organizations where the very real costs in operational complexity do not yield worthwhile benefits in agility or productivity.

The organizations where Kubernetes genuinely earns its overhead share specific characteristics: dedicated platform engineering teams who own the cluster as a product, polyglot service portfolios that benefit from a unified deployment model, workloads that genuinely require automated horizontal scaling and self-healing, and engineering teams with the discipline to build stateless services that the orchestration model assumes. Those organizations exist and Kubernetes serves them well.

The mismatch is with the gap between those conditions and the conditions that actually exist when most teams adopt Kubernetes. A Kubernetes cluster running three services that would have been equally well served by systemd units on a single VM, maintained by people learning Kubernetes on production infrastructure, generates operational complexity that costs more than it provides. The three services still run. The team now also maintains a Kubernetes cluster, etcd, a CNI plugin, an ingress controller, a certificate manager, and everything else the cluster requires — and debugs failures in each of those components in addition to the application failures they would have had anyway.

*The question worth asking before adopting Kubernetes is not 'is Kubernetes a good technology' but 'does our specific situation have the characteristics that make Kubernetes worthwhile.' A team that cannot answer yes to the organizational characteristics described above should consider whether a simpler deployment model — Docker Compose, managed container services, or even VMs — would provide the concrete benefits they need without the overhead they do not.*

### The Kubernetes Security Surface

Kubernetes adds a control plane that is one of the highest-value targets in any infrastructure environment. The API server, etcd (which contains all cluster state including secrets), and the service account token mechanism are all targets that did not exist before orchestration was introduced. This is the isolation reduction that orchestration makes: the cluster provides shared scheduling, shared secrets management, and shared networking across all workloads — the efficiency gain. The cost is that the control plane itself becomes a single high-value target whose compromise radius is the entire cluster.

- etcd contains everything: cluster configuration, workload specifications, and — critically — secrets stored in the cluster. etcd should be encrypted at rest, should have access controls that prevent read access by any account that does not need it, and should be backed up separately from cluster state. An attacker with read access to etcd has access to every Kubernetes secret in the cluster, which in most real environments includes credentials for external systems.

- RBAC misconfiguration is the most common Kubernetes security failure mode. Default service account tokens with excessive permissions, namespace admin roles that provide cluster-wide access through privilege escalation, and wildcard permissions granted to operators who needed one specific capability all create lateral movement paths that are invisible to someone thinking in VM terms.

- The blast radius of a compromised pod in a misconfigured cluster can extend to the entire cluster, all namespaces, and the external systems whose credentials are stored as secrets. This is a qualitatively different blast radius from a compromised VM, and it is the direct result of the consolidation efficiency that orchestration provides.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Compute Literacy | Can describe the compute stack in plain English: what a hypervisor does and what a VM is, what a container is and how it differs from a VM, what Kubernetes is and what problem it addresses. Can explain why the on-premises snapshot model does not map directly to cloud snapshots. Does not require operational experience with any specific platform. |
| Level 2 | Compute Audit | Can identify the blast radius of a compromise at each layer: what a hypervisor host compromise implies for every VM on it, what the shared kernel means for container isolation, what a misconfigured Kubernetes RBAC policy implies for cluster-wide access. Can identify when a workload's operational model (stateful/stateless, VM reflex/container reflex) is mismatched to its deployment environment. |
| Level 3 | Compute Commission | Can specify where a described workload belongs in the compute stack and why, accounting for performance requirements, operational overhead, security isolation requirements, and organizational capacity to manage the chosen platform. Can write the requirements for a Kubernetes workload that would justify the cluster's overhead versus one that would not. |
| Level 4 | Compute Design | Can design a compute architecture that matches workload characteristics to platform capabilities across the full stack. Can evaluate whether an organization's adoption of a given compute platform is justified by the problem it addresses or is adding complexity without proportional benefit. Can assess the security surface of a compute architecture across all layer transitions and identify the highest-value targets and their blast radii. |

## Assessment Exercises

### [LITERACY] The Wrong Model

*A sysadmin is debugging a containerized web application. The application is returning errors after a configuration change. They SSH into the running container, edit the configuration file directly, and the application begins working correctly. The next day the same errors return. What happened, why, and what is the correct approach?*

**Watch for:** Candidates who diagnose the problem as 'the container restarted' without explaining why the fix did not persist. The container filesystem is ephemeral — changes made to a running container exist only in that container's writable layer and are discarded when the container is replaced. The configuration fix worked in the running instance and was lost on the next deployment or restart because the image the container was launched from still had the original configuration. The correct fix is to update the image (or the configuration source the image reads from), not the running container. Candidates who recognize this as a VM-reflex-applied-to-containers failure mode are demonstrating the mindset shift the domain is building.

### [AUDIT] The Blast Radius Calculation

*A security audit identifies that a Kubernetes deployment has a service account with cluster-admin privileges bound to a pod that runs a web application exposed to the internet. The development team says this was done to allow the application to read its own deployment status. Candidate must identify the actual blast radius of this configuration, explain why the stated requirement does not justify the granted permission, and describe the minimum permission set that would meet the stated requirement.*

**Watch for:** Candidates who identify 'cluster-admin is too broad' without quantifying what cluster-admin actually means. Cluster-admin provides read and write access to every resource in every namespace in the cluster, including secrets. An attacker who compromises this web application through any vulnerability now has cluster-admin access and can read all secrets in etcd, modify any workload in the cluster, create privileged pods with host access, and potentially escape to the underlying node. The stated requirement — reading the deployment status — requires only a Role with get/list permissions on deployments in the specific namespace, not a ClusterRoleBinding to cluster-admin. This is the tiering model violation from Domain 2 expressed in Kubernetes terms.

### [AUDIT] The Azure Revert That Does Not Work

*A sysadmin is preparing to apply a risky OS-level change to an Azure VM. Their on-premises practice is to take a snapshot before risky changes and revert if something goes wrong. They take an Azure snapshot of the OS disk before making the change. The change breaks the VM. They attempt to revert to the snapshot and discover the process is different from what they expected. Explain what Azure snapshots actually are, what the correct pre-change protection mechanism is in Azure, and what the sysadmin should have done instead.*

**Watch for:** Candidates who describe the Azure snapshot as a bug or limitation rather than as a fundamentally different operation. An Azure snapshot is a point-in-time copy of a managed disk used for restoration — not a live checkpoint that can be reverted to while the VM runs. The correct pre-change protection in Azure is either a VM restore point (which captures all disks and some VM configuration), stopping the VM and swapping the OS disk to the snapshot (a more complex operation than on-premises revert), or provisioning a test environment where the change can be validated before applying to production. Candidates who can articulate the specific difference between the on-premises mental model and the Azure reality are demonstrating the abstraction-layer reasoning this domain builds.

### [COMMISSION] Where Does This Workload Belong

*Candidate is given four workloads and must specify where each belongs in the compute stack (bare metal, VM, container, managed container service, or serverless) with reasoning: (1) a legacy .NET Framework 4.5 application that requires a specific Windows Server version and has a local file dependency that cannot be refactored; (2) a stateless REST API written in Node.js deployed by a team that does three deployments per day; (3) a database server running PostgreSQL for a business-critical application with 99.9% availability requirement; (4) a batch processing job that runs nightly, takes 45 minutes, and is otherwise idle.*

**Watch for:** Candidates who recommend containers or Kubernetes for the legacy .NET application without addressing the Windows Server version dependency and local file state. Workload 1 belongs on a VM — containerization requires refactoring to remove the local file dependency, and a container running Windows Server 2012 R2 to satisfy a specific framework version is not the appropriate use of containerization. Workload 2 is the natural container candidate. Workload 3 belongs on a VM with appropriate storage and backup architecture — database servers benefit from predictable resource allocation and persistent storage that the container model complicates unnecessarily. Workload 4 is the natural serverless or managed container service candidate — the batch pattern maps directly to the pricing model of ephemeral compute.
