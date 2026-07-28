---
domain: 5
id: storage-architecture
title: "Storage Architecture"
subtitle: "Redundancy as probability management over time — not a binary protected/unprotected state"
reviewed: 2026-07-10
---

# Domain 5: Storage Architecture

*Redundancy as probability management over time — not a binary protected/unprotected state*

## Scope and the Disappearing Storage Expert

Ten years ago a mid-size organization might have had a dedicated SAN with Fibre Channel, a backup appliance, a NAS for file serving, and a storage administrator who understood all of it. Today the same organization probably has an HCI appliance or all-flash array for production, a NAS for file serving, and no dedicated storage person. The operational surface has shrunk, the specialist role has largely been absorbed into the platform, and the sysadmin who inherits this environment needs different knowledge than the storage architect who designed the previous generation.

This domain does not teach storage engineering. It teaches the reasoning a sysadmin needs to: recognize when a storage symptom is actually a storage problem versus a networking or application problem, understand what their specific platform's redundancy model implies about a given failure, know when they can address something themselves versus when they need vendor support, and ask the right questions when they do engage vendor support.

*The domain boundary with Domain 10 (Backup and Recovery): Domain 10 owns backup concepts, immutability requirements, retention policy, and recovery requirements definition. This domain owns the storage architecture that implements those requirements — performance characteristics, redundancy models, capacity planning, and the specific failure behavior of different storage configurations. Both domains are required to reason completely about protecting organizational data.*

## Reasoning Framework: Redundancy as Probability Management Over Time

How it is normally taught: storage redundancy is presented as a set of configurations with defined properties. RAID 5 tolerates one drive failure. RAID 6 tolerates two. RAID 10 mirrors data across pairs. The implication is that a RAID 5 array is protected storage with a simple indicator when it becomes degraded.

What it is actually for: storage redundancy is a mechanism for managing the probability of total data loss over a window of time. A RAID 5 array with a failed drive is not protected storage with a degraded indicator — it is unprotected storage with a narrow and closing window before total loss. The redundancy has already been consumed. The question is not whether the array is redundant but whether the remaining operational lifetime of the surviving drives is longer than the rebuild time. In large arrays with high-density drives, this calculation is not comfortable.

What misuse looks like: treating a degraded array as a normal operating state rather than an emergency. Treating successful RAID completion as evidence of data protection rather than evidence that redundancy has been restored. Not understanding that rebuild time scales with array size and that during rebuild, any additional drive failure causes total loss. The candidate who sees a RAID 5 array with one failed drive and thinks 'we have one more failure before we lose data' has the right model. The candidate who thinks 'we're fine, we have a hot spare' without understanding the rebuild window has not understood what redundancy actually provides.

*The same pattern as Domain 10's untested backup: a RAID array that has never experienced a drive failure and rebuild under production load is an untested redundancy mechanism. The rebuild that works fine at 2am on an otherwise idle array may behave very differently on an array servicing production workloads with aged drives during business hours.*

## The Storage Landscape: Then and Now

### The Collapse of the Middle

The storage market below the high end has collapsed toward two poles: dumb NAS and all-flash HCI. The elaborate middle tier — dedicated SANs, Fibre Channel fabrics, tiered storage with automated data movement — still exists in large enterprises and specialized environments, but for the organizations a sysadmin without a dedicated storage team is likely to work in, the choice is increasingly simple.

This is largely a good development operationally. HCI platforms like Nutanix, vSAN, and Azure Stack HCI abstract storage complexity behind the hypervisor layer and provide redundancy models that are simpler to reason about than traditional SAN architectures. NAS appliances from vendors like Synology and QNAP provide file services with reasonable redundancy at cost points that make dedicated storage infrastructure unnecessary for most workloads.

### Fibre Channel: Context Without Curriculum

Fibre Channel was valuable because it provided a dedicated, deterministic, low-latency storage fabric that did not contend with general network traffic and had mature tooling for large-scale block storage. Those properties still matter at the scale that justifies FC infrastructure, which is why it persists in large enterprises and specialized environments.

It is not a skill a sysadmin without a dedicated storage team needs to develop. If you encounter FC in the wild it will be in an environment that has it for specific reasons and is managed by someone who understands it. Your job is to know enough to not break it inadvertently rather than to administer it. The relevant knowledge is: FC is a dedicated storage fabric, not general networking; FC ports and FC switches are purpose-built infrastructure; FC zoning is the access control mechanism; and any change to FC infrastructure requires engagement with whoever manages it, not experimentation.

### Hardware RAID to Software-Defined Storage

Traditional hardware RAID is a synchronous, local, hardware-enforced redundancy mechanism where the failure domain is the RAID set. The controller presents the array as a single logical disk. The firmware handles recovery. The administrator's role in a failure is to replace the failed drive and monitor the rebuild.

Software-defined storage (Nutanix, vSAN, Storage Spaces Direct) distributes data and redundancy across nodes using replication factors or erasure coding at the software layer. The disk is dumb — an HBA in JBOD mode presents individual drives to the software layer, which makes all redundancy decisions. The administrator's role changes from managing a hardware abstraction to monitoring a distributed system whose behavior during failure is more complex and less familiar.

- Replication factor: data is written to N copies across different nodes. A replication factor of 2 means two copies on two different nodes. A single node failure is tolerated. The rebuild involves reading from surviving copies and writing new copies on remaining nodes — different from RAID rebuild in both mechanism and time characteristics.

- Erasure coding: data is striped across nodes with parity information distributed across the stripe. More storage-efficient than full replication at the cost of write amplification and more complex recovery. The failure tolerance depends on the coding scheme; common schemes tolerate 1-2 node failures.

- The failure domain shift: traditional RAID fails at the drive level. Software-defined storage fails at the node level. A node failure takes all the drives in that node offline simultaneously. The redundancy model needs to account for node failure, not just drive failure.

## Core Storage Concepts

### The Spinning Disk vs. SSD Tradeoff Is Not About Speed

The candidate who thinks SSD is obviously better than spinning disk is making the same reasoning error as the candidate who thinks RAID 5 is obviously better than JBOD — treating performance as the only axis. For workloads where performance is the binding constraint, SSD is correct. For workloads where capacity per dollar is the binding constraint, spinning disk remains decisively better.

- Cost per TB: high-density spinning disk (18-22TB enterprise drives) is dramatically cheaper per TB than SSD at equivalent capacity. The gap has narrowed but has not closed. For backup-to-disk, archive, large-file media workflows, and cold storage, the performance disadvantage of spinning disk is irrelevant and the cost advantage is decisive.

- Power and density: at bulk storage scale, high-density spinning disk arrays deliver more usable TB per watt and per rack unit than equivalent SSD configurations. For organizations managing petabytes of warm or cold data, this is a real operational consideration.

- Endurance for write-heavy workloads: SSD write endurance is finite and measurable. High write-rate workloads — database transaction logs, surveillance video, high-frequency logging — will wear out SSDs at a rate that makes drive replacement cost a meaningful budget consideration. Enterprise SSDs are rated for write endurance; the correct question for a write-heavy workload is not just performance but whether the endurance rating matches the write rate.

### IOPS, Throughput, and Latency: The Three Performance Axes

Storage performance is three separate measurements that are frequently conflated. Getting the relationship between them wrong produces misdiagnosis when applications are slow.

- IOPS (input/output operations per second): the number of read or write operations the storage can service per second. Relevant for workloads with many small, random I/O operations — databases, virtual machine boot storms, transactional applications.

- Throughput (MB/s): the volume of data that can be transferred per second. Relevant for workloads with large sequential I/O — backup jobs, large file transfers, streaming media, analytics against large datasets.

- Latency (ms): the time between issuing an I/O request and receiving a response. Relevant for all workloads but critical for latency-sensitive applications where the application is waiting for storage to respond before proceeding.

The symptom/cause relationship from Domain 8 applies directly: an application that is timing out or running slowly may be experiencing storage latency, storage IOPS exhaustion, or storage throughput saturation — or none of the above. The correct diagnostic path is to measure storage metrics (queue depth, latency, IOPS utilization, throughput utilization) against the storage system's rated limits before concluding that storage is the cause. High queue depth with elevated latency is a meaningful signal. High IOPS utilization with normal latency may not be a problem.

### Thin Provisioning: Commitments You Cannot Always Keep

Thin provisioning is widely described as 'using less space' by presenting a larger logical disk than the physical storage that backs it. The accurate description is making promises about future storage availability that may not be kept.

A thin-provisioned datastore or volume presents 10TB to the guest while 3TB of physical storage backs it, on the assumption that the guest will not use all 10TB simultaneously. This assumption is correct most of the time and catastrophically wrong when it fails. When the physical backing storage fills completely, write operations across every thin-provisioned guest on that datastore fail simultaneously. Not gradually — simultaneously. All VMs sharing the datastore encounter write failures at the same moment, which typically causes application crashes, data corruption in open files, and in the worst case VM unresponsiveness across the entire shared storage pool.

*Thin provisioning overcommit is the storage equivalent of the ransomware retention timing problem from Domain 10: everything appears healthy until it doesn't, the failure is total rather than gradual, and the moment of failure is the worst possible time to discover the underlying condition. Monitoring physical space utilization on thin-provisioned datastores is not optional — it is the control that prevents a silent accumulation from becoming a total outage.*

### Cloud Storage: The Abstraction Layer and Where It Lies

Cloud storage presents familiar concepts — disks, IOPS, throughput — through an abstraction layer that obscures physical properties in ways that surface under load. The sysadmin who carries on-premises mental models into cloud storage without adjustment will be surprised.

- Burst versus sustained performance: many cloud storage tiers offer burst IOPS that are significantly higher than the sustained baseline. A P10 Azure managed disk has a burst IOPS ceiling that makes performance testing look excellent, and a sustained IOPS baseline of 500 that produces severely degraded performance under continuous production load. The burst bucket fills during idle periods and drains under sustained load. A workload that performs well in testing because testing doesn't exhaust the burst bucket will fail under production load that does. This is not a documentation footnote — it is a fundamental property of the pricing tier that determines whether the storage tier is appropriate for the workload.

- VM-size throughput caps: in most cloud environments, storage throughput is capped at the VM size level, not just the disk tier level. A VM that is undersized for its workload may hit the VM-level throughput cap before the disk-level cap. Diagnosing storage performance issues in cloud requires checking both the disk tier limits and the VM size limits simultaneously.

- Network-attached storage latency floor: cloud managed disks are network-attached storage regardless of how they are presented to the guest. The latency floor is higher than locally attached NVMe and the variance is higher than dedicated storage arrays. Latency-sensitive workloads that perform reliably on dedicated all-flash on-premises may perform inconsistently on cloud managed storage due to network-attached latency characteristics.

The honest assessment posture for cloud storage: the performance characteristics of cloud storage tiers are specified in documentation, but the documentation describes limits rather than behavior. Actual behavior under sustained production load requires testing against the specific workload pattern, not just reading the specification. Cloud providers optimize storage for the common case, and the common case is not necessarily your case.

### Backup Storage Requirements Are Not Production Storage Requirements

The storage architecture that hosts backup data has different requirements than production storage, and treating them identically is a mistake. Domain 10 established the requirements: credential separation at a separate trust tier, immutability against production credential access, retention depth that addresses the threat model. This domain adds the storage architecture layer: what those requirements mean for the physical or logical storage configuration.

- Performance requirements for backup storage are write-intensive and sequential, which favors high-capacity spinning disk over SSD. The workload pattern is sustained large sequential writes during backup windows, occasional large sequential reads during restore operations, and idle otherwise. SSD's advantages — low latency, high random IOPS — are largely irrelevant for this workload. High-density spinning disk's advantages — high capacity per dollar, high throughput for sequential operations — directly address it.

- Immutability requirements mean the backup storage architecture must prevent deletion or modification by the credentials used to access production systems. This is an access control requirement, not a storage performance requirement, but it constrains the architectural choices: the storage must be on a separate trust tier, managed through separate authentication, and ideally provide object-level immutability that prevents overwrite even by the backup account.

- Capacity planning for backup storage must account for retention depth and deduplication ratios together. A 90-day retention policy with daily backups of a 10TB dataset sounds like 900TB of storage, but deduplication against a slowly-changing dataset may reduce this dramatically. Getting this calculation wrong in either direction — underestimating and running out of space, overestimating and overprovisioning — has operational consequences worth modeling before purchasing.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Storage Literacy | Can describe storage configurations in plain English: what RAID levels provide and what they do not, what thin provisioning is and what overcommit means, what IOPS and throughput measure and why they are different. Can read a storage system's health indicators and describe what they mean without being able to diagnose the underlying cause. |
| Level 2 | Storage Audit | Can identify configurations that present higher risk than they appear: RAID arrays with aged drives where rebuild time exceeds expected drive lifetime, thin-provisioned datastores approaching physical capacity, storage tiers with burst performance characteristics being used for sustained workloads. Can identify when an application performance complaint is likely storage-related and what measurements would confirm or rule it out. |
| Level 3 | Storage Commission | Can specify storage requirements for a described workload: performance tier, redundancy model, capacity with growth projection, backup storage requirements separate from production, cloud tier selection with honest assessment of burst versus sustained characteristics. Can evaluate whether a proposed storage architecture meets the stated requirements. |
| Level 4 | Storage Design | Can design a storage architecture that addresses production, backup, and archive requirements as distinct tiers with distinct characteristics. Can reason about the rebuild window risk of a degraded array under production load. Can evaluate whether a cloud storage tier is appropriate for a specific workload pattern by testing against sustained load rather than accepting burst performance as representative. |

## Assessment Exercises

### [AUDIT] The Degraded Array

*A storage array alert shows that a RAID 5 array has a failed drive. The array has 8 drives of 14TB each. Current utilization is 60%. The hot spare has begun rebuilding automatically. The estimated rebuild time shown in the management interface is 18 hours. The array is servicing a production database workload. Candidate must assess the risk profile during the rebuild window, identify what makes this more or less risky than the interface's simple 'degraded — rebuilding' status implies, and describe what monitoring and contingency planning is appropriate during the rebuild.*

**Watch for:** Candidates who treat the hot spare rebuild as sufficient risk mitigation without addressing the rebuild window vulnerability. An 18-hour rebuild on a production database array with aged drives means 18 hours of zero fault tolerance — any second drive failure during that window causes total data loss. The production database workload increases I/O on the surviving drives during rebuild, which increases the probability of a second failure. The correct response includes: escalating urgency to management, increasing monitoring frequency, verifying backup recency and restorability, considering whether the production workload should be reduced or migrated during the rebuild window, and having a documented response plan for a second drive failure during rebuild.

### [AUDIT] The Thin Provisioning Alarm

*A monitoring alert shows that a vSphere datastore is at 87% capacity. The datastore is thin-provisioned, presenting 20TB to twelve VMs while 3.8TB of physical storage remains. Three of the VMs are running database workloads with active transaction logs. Candidate must assess the risk, identify the specific failure mode if capacity is exhausted, and describe the immediate and medium-term response.*

**Watch for:** Candidates who treat 87% as a capacity planning concern rather than an emergency. At 87% of a thin-provisioned datastore with database workloads, the failure scenario is imminent and the failure mode is simultaneous write failures across all twelve VMs. The immediate response is to stop non-critical VM writes and expand the datastore or migrate VMs to available storage — not to open a change request for next week's maintenance window. The medium-term response is to convert thin-provisioned VMs to thick provisioning or maintain a hard capacity reservation that prevents the physical storage from being fully allocated.

### [AUDIT] The Cloud Storage Complaint

*A developer reports that a database on an Azure VM is performing well during testing but has unacceptable latency in production. The VM is Standard_D4s_v3. The OS disk is a P10 managed disk. The database data files are on a P20 managed disk. Testing was conducted with a dataset that fit entirely in the database buffer cache. Production workload involves sustained random reads against a dataset that exceeds the buffer cache. Candidate must identify the likely storage performance bottleneck and explain why testing did not reveal it.*

**Watch for:** Candidates who recommend upgrading the disk tier without investigating whether the burst bucket exhaustion is the actual mechanism. The P10 OS disk is unlikely to be the constraint. The P20 data disk has a baseline of 2300 IOPS and a burst ceiling significantly higher. Testing with a cached dataset produced I/O that fit in memory, not storage — so the storage was not actually exercised. Production with a dataset exceeding the cache produces sustained random reads against the P20's baseline, not its burst capability. The correct diagnosis requires checking whether the disk is hitting its sustained IOPS limit, and whether the Standard_D4s_v3 VM's uncached disk throughput limit is being reached before the disk limit. Both need to be checked before a solution can be specified.

### [COMMISSION] Specify the Storage Architecture

*Candidate must specify a storage architecture for a small organization with the following workloads: a primary business application on three VMs requiring consistent low-latency storage, a file server used by 50 users for document storage and collaboration, a backup target for daily backups of all VMs retained for 90 days, and cold archive storage for compliance documents retained for 7 years. Candidate must specify the appropriate storage tier for each workload, the redundancy model, the capacity estimate, and the separation between production and backup storage.*

**Watch for:** Specifications that use a single storage tier for all workloads. The correct architecture differentiates: all-flash or high-performance SSD-backed storage for the production VMs, NAS with spinning disk for the file server, separate high-capacity spinning disk or object storage for backup with appropriate access controls, and either cold cloud storage or deep archive media for 7-year compliance retention. Candidates who specify the same tier for backup and production storage have not understood the Domain 10 requirement for credential separation and access control isolation between production and backup.
