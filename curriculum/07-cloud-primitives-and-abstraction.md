---
domain: 7
id: cloud-primitives-and-abstraction
title: "Cloud Primitives and Abstraction"
subtitle: "The approximation map — where cloud represents underlying concepts faithfully and where it specifically does not"
reviewed: 2026-07-10
---

# Domain 7: Cloud Primitives and Abstraction

*The approximation map — where cloud represents underlying concepts faithfully and where it specifically does not*

## Scope and Relationship to Prior Domains

This domain synthesizes the cloud-specific content introduced throughout the framework — the Azure snapshot divergence from Domain 6 (Compute Architecture), the burst IOPS problem from Domain 5 (Storage Architecture), the cloud networking model from Domain 3 — and extends it to the operational and governance layer. It covers the three major cloud platforms (AWS, Azure, GCP) at a conceptual depth that rewards provider-specific experience without requiring it. Real syntax and real service names are used throughout because part of being a sysadmin is research, and the candidate who encounters an unfamiliar service name should be able to look it up rather than need it pre-explained.

This domain does not teach cloud certification content. AZ-104, AWS SAA, and GCP ACE cover cloud vocabulary adequately. What they do not cover is the translation layer: understanding what a cloud primitive is actually doing underneath the abstraction, where the abstraction faithfully represents the underlying concept, and where it diverges in ways that produce surprises under load, under failure, or under cost pressure.

*The domain's central argument: cloud providers have invested billions in their specific primitives. When you use them, you receive the benefit of that investment. When you avoid them for theoretical portability, you pay cloud pricing while receiving the operational value of running your own datacenter on rented hardware.*

## Reasoning Framework: The Approximation Map

How it is normally taught: cloud services are presented as equivalents to on-premises concepts. EC2 is a virtual machine. S3 is object storage. Azure VMs are virtual machines. The implicit model is that the translation is faithful and the operational experience will be similar.

What it is actually for: cloud primitives approximate on-premises concepts with specific divergences that matter operationally. The approximation map has two dimensions — where the model is faithful enough that on-premises intuitions transfer reliably, and where the model diverges in ways that produce failures, surprises, or missed opportunities if the on-premises mental model is applied without adjustment.

What misuse looks like: treating cloud primitives as drop-in replacements for their on-premises equivalents and discovering the divergence points in production. The Azure snapshot that does not support in-place revert the way VMware snapshots do. The P10 managed disk that performs like enterprise SSD in testing and like consumer hardware under sustained production load. The security group that appears to function like a firewall rule set but has stateful behavior that is different from what the on-premises firewall provides. Each of these is a case where the on-premises mental model was applied and the approximation's limits became visible.

## The Abstraction Chain: From Hardware to Managed Service

The cloud managed service model is the latest iteration of a tradeoff that sysadmins have been making for decades. The progression is continuous and each step makes the same exchange:

- Vendor-qualified physical hardware: maximum control and transparency, maximum operational burden. You own the firmware, the hardware replacement cycle, the failure diagnosis. You also have full visibility into what is happening and why.

- VM appliance (vendor-qualified VM image): the hardware abstraction is gone, the software stack is still vendor-controlled. Slightly less operational burden, slightly less transparency into the appliance internals.

- Software package on a VM you manage: you control the infrastructure and the operating system, the software is from a vendor. You can see everything, you are responsible for everything.

- Platform as a Service (App Service, Cloud Run, Elastic Beanstalk): you provide the application code, the platform manages the runtime, OS, and scaling. You cannot see or control what happens below the application layer.

- Managed database, cache, or queue (RDS, Cloud SQL, Azure SQL): you provide the schema and the application connection, the provider manages the database engine, patching, backups, and failover. You cannot tune the OS or replace the storage.

- Fully managed analytics or ML service (BigQuery, Azure Synapse, SageMaker): you provide the data and the query or model, the provider manages everything else. There is frequently no on-premises equivalent and no portability path.

At each step the operational burden decreases and the opacity increases. This is not a failure of the managed service model — it is its design. The correct evaluation question at each step is not 'is this more or less managed' but 'do the limitations imposed by this abstraction level affect anything I need to control, and is the operational burden reduction worth the opacity?'

*The sysadmin who reaches for a managed service and discovers six months later that it cannot be tuned for their workload, cannot be monitored at the level they need, or cannot integrate with their existing security tooling has paid the opacity cost without understanding it in advance. The evaluation should happen before the architecture decision, not after the workload is running.*

## Core Primitives: Where the Big Three Align and Diverge

### Compute

All three major providers offer virtual machines with broadly similar properties: you specify CPU, memory, and storage, you get a VM, it runs your workload. The abstractions diverge in operationally significant ways.

- Instance families: AWS EC2, Azure VMs, and GCP Compute Engine all organize instances into families optimized for different workload types (general purpose, memory-optimized, compute-optimized, storage-optimized). The families are not equivalent across providers — an AWS r6i.xlarge and an Azure E4s v5 are both memory-optimized but have different CPU architectures, memory-to-CPU ratios, and network throughput characteristics. Right-sizing for a specific workload requires evaluating the specific instance type, not just the family label.

- Burstable instances: AWS T-series, Azure B-series, and GCP E2 instances provide baseline CPU with burst capability using a credit model. The credit accumulation rate, burst ceiling, and behavior when credits are exhausted differ across providers. A workload that fits comfortably on a T3.medium may behave differently on an equivalent Azure B-series instance under the same load pattern.

- Bare metal and dedicated hosts: all three providers offer options for workloads that require dedicated physical hardware — license compliance, security isolation, NUMA-sensitive applications. The pricing model and provisioning lead time differ significantly.

- Spot/preemptible/spot VMs: AWS Spot, Azure Spot VMs, and GCP Spot VMs all offer significantly discounted compute with interruption risk. The interruption notice period, the frequency of interruption, and the pricing volatility differ. GCP Spot VMs historically have higher interruption rates than AWS Spot in many regions.

### Networking: Where the Architectural Differences Are Largest

Cloud networking models diverge from on-premises networking and from each other in ways that make direct translation unreliable. The most consequential differences are in the default network topology and what the provider's documentation assumes you will do.

- AWS requires explicit VPC design. Every account has a default VPC that is adequate for experimentation and dangerous for production (it is flat, public-facing by default, and shared across all resources in the account). Real AWS architecture requires deliberate subnet design, route table configuration, internet gateway and NAT gateway placement, and security group layering. The VPC is the primary network boundary.

- Azure VNets are optional and additive. Many Azure services work without a VNet. The recommended Hub-Spoke topology is architecturally different from AWS VPC peering models. Azure Private Endpoints and Service Endpoints provide different mechanisms for securing managed service access than AWS VPC Endpoints, despite similar names. The Azure network security model with NSGs (Network Security Groups) at the subnet and NIC level is specifically different from AWS security groups, which are instance-level and stateful.

- GCP uses a global VPC model where subnets are regional but the VPC itself spans all regions. This is architecturally distinct from AWS and Azure, where VPCs and VNets are regional constructs. Traffic between GCP subnets in different regions traverses Google's private backbone by default without requiring explicit peering. This changes the latency and cost model for multi-region architectures.

- Broadcast and multicast: as established in Domain 3, cloud virtual networks do not support broadcast or multicast traffic. Protocols that depend on broadcast for discovery (older Windows file sharing, some network appliance management protocols) do not function without workarounds. This is consistent across all three providers.

### IAM: The Same Problem, Three Different Models

Identity and access management is where the divergence between providers creates the most organizational friction for multi-cloud or provider-switching scenarios. The conceptual goal is the same — control what identities can do what to which resources — but the models differ enough that expertise in one does not transfer reliably.

- AWS IAM is resource-centric and explicit. Permissions are policies attached to identities or resources. The interaction between identity policies and resource policies (S3 bucket policies, KMS key policies) requires understanding both sides. IAM Roles for EC2 (and equivalent mechanisms for other compute services) provide instance-level credential-free access to AWS services — the correct alternative to long-lived access keys on instances.

- Azure RBAC is scope-based with a hierarchy: management group → subscription → resource group → resource. Role assignments at a higher scope inherit down. Azure Managed Identities provide credential-free access to Azure services for VMs, App Service, and other compute — system-assigned (tied to the resource lifecycle) and user-assigned (reusable across resources) serve different operational patterns.

- GCP Cloud IAM follows a resource hierarchy: organization → folder → project → resource. The project is the fundamental billing and access boundary. GCP Service Accounts are the credential-free access mechanism for compute workloads — they are more explicitly visible as distinct identities than AWS IAM Roles or Azure Managed Identities, and the permission to impersonate a service account (iam.serviceAccounts.actAs) is a frequently misconfigured path for privilege escalation.

- The shared failure mode: long-lived credentials (AWS access keys, Azure service principal client secrets, GCP service account JSON keys) stored in environment variables, configuration files, or source code. All three providers have native credential-free mechanisms that eliminate this risk for workloads running on their platforms. Using them is the correct default; using long-lived credentials for internal workloads is a design decision that should be explicitly justified, not an unreflective default.

### Storage: Tiers, Durability, and the Performance Model

Cloud object storage (S3, Azure Blob Storage, GCS) has no direct on-premises equivalent and is one of the areas where the cloud model is genuinely different rather than an abstraction of something familiar. Block storage (EBS, Azure Managed Disks, Persistent Disks) is closer to what sysadmins know from on-premises storage but diverges in specific ways established in Domain 5 (Storage Architecture).

- Object storage durability guarantees are expressed as nines (11 nines for AWS S3 Standard) and represent the probability of object loss in a given year, not a guarantee of availability. The durability model assumes multiple availability zones storing copies — for single-AZ configurations (S3 One Zone-IA, Azure Locally Redundant Storage) the durability guarantee is lower. Understanding what durability tier your data is on and what failure scenario it does and does not protect against is a basic storage architecture check.

- Storage tiers and cost: all three providers offer multiple storage tiers with different access cost, retrieval latency, and storage cost tradeoffs — similar to the hot/warm/cold storage model from Domain 5 (Storage Architecture). AWS S3 Intelligent-Tiering automates movement between tiers; GCS has Autoclass. Unmanaged data lifecycle policies are one of the primary drivers of unexpected cloud storage costs.

- The burst IOPS problem from Domain 5 (Storage Architecture) applies here: managed disk tiers across all providers have baseline and burst performance characteristics. The P10 managed disk in Azure, the gp2 EBS volume in AWS, and the pd-balanced in GCP all have performance characteristics that look better in testing than under sustained production load. The correct evaluation is against the sustained baseline, not the burst ceiling.

## The Portability Argument: What It Protects Against and What It Does Not

The argument for cloud-agnostic infrastructure design is primarily a hedge against vendor leverage — the fear that a cloud provider will impose significant cost increases, change terms unacceptably, or exit the market in a way that forces migration. It is worth evaluating this argument against actual risk rather than theoretical scenarios.

The closest real-world analog to the scenario the portability argument defends against is the Broadcom acquisition of VMware. Broadcom significantly restructured VMware's licensing and pricing model, creating urgency around migration for many organizations. The mechanism was price and licensing changes, not technical incompatibility — the workloads themselves were not changed. Critically, a cloud-agnostic Terraform strategy would not have helped. Organizations running VMware on-premises with cloud-agnostic tooling were in the same position as those using VMware-specific tooling: their workloads ran on VMware, and VMware's pricing had changed. The protection against this class of risk is actual portability of workloads — applications that can run on different infrastructure — not infrastructure provisioning tooling that abstracts away provider-specific APIs.

The major cloud providers (AWS, Azure, GCP) have not executed a VMware-style pricing rugpull on their core infrastructure services. Core primitives — VMs, object storage, managed databases — have generally become cheaper over time as competition and efficiency improvements reduce costs. The risk of sudden dramatic price increases on established services is real but has not materialized at the scale the portability argument assumes. This is not a guarantee about the future, but it is relevant to a risk assessment.

The actual cost of cloud-agnostic design: you are not using the primitives that make the cloud platform good at what it is good at. You are paying cloud pricing to run workloads with the operational characteristics of self-managed infrastructure. The networking topology avoids VPC-specific features and is suboptimal everywhere. The IAM strategy avoids managed identities and uses long-lived credentials that are a security liability. The storage architecture avoids lifecycle policies and accumulates unnecessary cost. The theoretical benefit is flexibility you may never exercise. The actual cost is borne now, continuously, in security debt, operational overhead, and underutilized platform capability.

*The correct version of portability investment is at the application layer, not the infrastructure tooling layer. Applications that externalize state, use standard protocols, avoid proprietary APIs at the business logic level, and can be redeployed to different infrastructure are portable. Terraform modules that work across providers while using none of them well are not portability — they are a lowest-common-denominator consumption strategy that leaves platform value on the table.*

## Cost, FinOps, and the TCO Reality

Cloud is not cheaper than on-premises by default. It converts capital expenditure to operational expenditure, which has real accounting and cash flow value. It provides elasticity that reduces the cost of handling variable or unpredictable demand. It eliminates the operational burden of managing physical infrastructure. These are genuine benefits. They do not automatically produce lower total cost of ownership.

Organizations that lift-and-shift workloads to cloud without rightsizing, without reserved capacity commitments, without autoscaling, and without understanding the billing model frequently pay more than they did on-premises. The cloud billing model is designed to charge for consumption — it does not automatically optimize that consumption. The on-premises model forces efficiency by imposing a fixed cost regardless of utilization; the cloud model charges for every hour of every resource, which produces high bills when resources are overprovisioned and idle.

- Reserved instances / committed use: AWS Reserved Instances, Azure Reserved VM Instances, and GCP Committed Use Discounts provide significant discounts (30–70%) in exchange for committing to a resource type for one or three years. For stable, predictable workloads, not using reserved capacity is one of the most common sources of avoidable cloud spend.

- Right-sizing: cloud instances are easy to resize and the cost difference between sizes is linear. An application running on an instance that is consistently at 15% CPU utilization is overprovisioned and paying for resources it does not use. Right-sizing is not a one-time activity — it should be revisited as workloads change.

- Storage lifecycle policies: unmanaged data in object storage accumulates. Data that was frequently accessed two years ago may now be accessed rarely or never. Without lifecycle policies that move data to cheaper tiers or delete it, the storage bill grows continuously regardless of whether the data has value.

- Egress costs: data moving out of cloud provider networks is charged per GB on AWS and GCP; Azure's model differs but has its own complexity. Applications that generate high egress traffic — CDN-heavy workloads, cross-region data transfer, data export to on-premises — accumulate egress costs that are frequently underestimated at architecture time.

FinOps (Financial Operations) is the discipline of applying financial accountability to cloud consumption. It exists because cloud billing is complex, often surprising, and not automatically optimized. A sysadmin who understands the basics — reserved vs. on-demand pricing, rightsizing, lifecycle policies, egress costs — is better positioned to avoid the most common sources of waste than one who treats billing as someone else's problem.

## Provider Hierarchy and Governance Differences

The organizational structures above the individual resource differ enough across providers that governance strategies that work well on one platform require real adaptation on another — not just vocabulary changes but conceptual changes in how access control, billing, and policy enforcement are organized.

- AWS uses Organizations with accounts as the primary isolation boundary. A well-architected AWS environment separates workloads into dedicated accounts (one account per environment, or one per application). Accounts provide billing isolation, IAM isolation, and service quota isolation. Cross-account access uses IAM role assumption. AWS Control Tower and Service Control Policies provide governance at the organization level.

- Azure uses management groups above subscriptions, with subscriptions as the primary billing and access boundary. Resource groups are the operational grouping unit within a subscription. Azure Policy at the management group level enforces governance across all child subscriptions. Entra ID tenants provide the identity layer that is shared across subscriptions in an organization.

- GCP uses a hierarchy of organization → folders → projects. The project is the fundamental billing, API enablement, and access boundary — equivalent in some ways to an AWS account but with different isolation properties. GCP Organization Policies provide governance constraints at the organization or folder level. Service account permissions are scoped to projects, which changes how service-to-service authentication is structured compared to AWS and Azure.

*A governance model designed for one provider's hierarchy does not translate cleanly to another's. The Azure Policy structure that enforces tagging and region restrictions across all subscriptions has no direct AWS equivalent — it requires a combination of Service Control Policies, AWS Config Rules, and account-level enforcement. Evaluating whether a governance requirement is implementable on a given provider requires understanding the provider's hierarchy, not just the requirement.*

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Cloud Literacy | Can describe the core primitives of at least one major cloud provider accurately: compute, storage, networking, and IAM at the conceptual level. Can explain the abstraction chain from hardware to managed service and what is traded at each step. Can identify which cloud provider-specific services have no direct on-premises equivalent. |
| Level 2 | Cloud Audit | Can identify where a described cloud architecture is using provider-native capabilities appropriately versus where it is applying on-premises patterns that do not translate well. Can identify long-lived credentials where managed identity mechanisms should be used. Can assess whether a storage tier, compute instance type, or networking topology is appropriate for the described workload. |
| Level 3 | Cloud Commission | Can specify a cloud architecture for a described workload that uses provider-native capabilities appropriately, accounts for performance characteristics accurately (burst vs. sustained), and addresses IAM with managed identities rather than long-lived credentials. Can evaluate whether a proposed cost optimization approach will actually reduce spend or redistribute it. |
| Level 4 | Cloud Design | Can design a governance structure appropriate for a described organizational hierarchy on a specific cloud provider. Can evaluate whether a portability strategy is providing actual protection against the risks it claims to address or adding complexity for theoretical benefit. Can assess the TCO of a described architecture including reserved capacity, right-sizing opportunities, and lifecycle policies. |

## Assessment Exercises

### [AUDIT] The On-Premises Mental Model Fails

*A team is migrating a workload from on-premises VMware to Azure. Before migration they take VMware snapshots of all VMs as a safety net — their standard practice before risky changes. After migration they run a test that reveals a configuration problem. They attempt to revert to the pre-migration snapshot and discover they cannot. Explain what happened, why the mental model failed, and what the correct pre-migration protection mechanism in Azure would have been.*

**Watch for:** Candidates who describe Azure snapshots as a bug or limitation rather than a fundamentally different primitive. Azure snapshots of managed disks are point-in-time copies for restoration, not live checkpoints for revert. The VMware snapshot mechanism (live state chain with revert capability) has no direct Azure equivalent in the same operational pattern. The correct pre-migration protection is Azure VM restore points, stopping the VM and swapping the OS disk from snapshot, or a staging environment where the migration is validated before production. Candidates who can articulate the specific difference between the on-premises mental model and the Azure primitive are demonstrating Level 2 reasoning.

### [AUDIT] The Credential Audit

*A security review of an AWS environment reveals the following: three EC2 instances with IAM access keys stored in environment variables; two Lambda functions using long-lived IAM user credentials; one RDS instance with a hardcoded master password in a CloudFormation parameter; and four S3 buckets without lifecycle policies. Candidate must identify which findings represent architectural problems versus configuration problems, explain the correct AWS-native mechanism for each credential issue, and prioritize the findings by risk.*

**Watch for:** Candidates who treat all four findings as equally urgent without distinguishing architectural from configuration issues. The EC2 instances with hardcoded access keys and Lambda functions with long-lived credentials are architectural problems — IAM Roles for EC2 and Lambda execution roles with appropriate permissions are the correct native mechanisms that eliminate the need for credentials entirely. The RDS master password is a configuration problem addressable with Secrets Manager rotation. The S3 lifecycle policies are a cost and hygiene issue, lower priority than the credential exposure. Candidates who understand that managed identity mechanisms (IAM Roles) exist specifically to eliminate long-lived credentials for workloads running on AWS infrastructure are demonstrating cloud-native reasoning.

### [COMMISSION] The Portability Decision

*An organization is designing their cloud infrastructure strategy. A consultant has recommended using only Terraform with provider-agnostic modules, avoiding managed identity mechanisms in favor of service principal credentials to maintain portability, and using only services available on all three major clouds. The stated reason is that the organization wants to avoid vendor lock-in. Candidate must evaluate this recommendation: what risk it actually addresses, what it costs operationally and from a security perspective, and whether the portability it provides is the portability that protects against the stated concern.*

**Watch for:** Candidates who accept the portability recommendation at face value. The recommendation addresses the risk of needing to migrate workloads to a different provider. The cost is: service principal credentials with client secrets instead of managed identities (a real and ongoing security liability), limiting the architecture to the lowest common denominator of services available on all three clouds (excluding most managed services that provide genuine operational value), and Terraform complexity that does not actually make workloads portable at the application layer. The protection it provides is at the provisioning tooling layer, not the application layer — the workloads themselves still depend on whatever cloud services they consume, and those dependencies would need to be rebuilt regardless of whether Terraform or provider-native IaC was used. Candidates who identify that actual portability requires application-layer investment, not infrastructure tooling uniformity, are demonstrating Level 4 reasoning.

### [AUDIT] The TCO Surprise

*An organization migrated from on-premises to AWS two years ago. Their monthly AWS bill is 40% higher than their on-premises infrastructure cost was. A review reveals: all instances are on-demand with no reserved capacity; three instances are consistently at under 20% CPU utilization; S3 contains 50TB of data with no lifecycle policies, of which access logs show 45TB has not been accessed in over a year; and a data pipeline generates 8TB of cross-region data transfer per month. Candidate must identify the primary cost drivers, estimate which interventions would produce the largest cost reduction, and explain what FinOps practice would have caught these earlier.*

**Watch for:** Candidates who recommend switching cloud providers as the solution to higher-than-expected TCO. The cost drivers are specific and addressable: reserved instances for the consistently-used compute would reduce that cost by 30-70%; right-sizing the underutilized instances would reduce compute cost; moving the 45TB of unaccessed S3 data to S3 Glacier Instant Retrieval or Glacier Deep Archive would reduce storage cost dramatically; and the cross-region egress may warrant architectural changes (caching, data locality) or may be acceptable at current costs. The FinOps practice that would have caught this is cost allocation tagging combined with budget alerts and periodic right-sizing reviews — none of which are automatic, all of which require deliberate operational investment.
