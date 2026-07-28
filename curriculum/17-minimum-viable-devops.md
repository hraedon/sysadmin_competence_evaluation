---
domain: 17
id: minimum-viable-devops
title: "Minimum Viable DevOps: Git, Containers, Orchestration"
subtitle: "Not platform engineering — the functional floor for operating in environments where these are load-bearing"
reviewed: 2026-07-10
---

# Domain 17: Minimum Viable DevOps: Git, Containers, Orchestration

*Not platform engineering — the functional floor for operating in environments where these are load-bearing*

## Scope and Framing

This domain follows the pattern established by Domain 12 (Minimum Viable Linux Administration): the functional floor, not expertise. A modern sysadmin encounters Git, containers, and Kubernetes in enough operational contexts that lacking a working vocabulary in any of the three is a genuine liability. The goal is not to produce a platform engineer. The goal is to operate competently in environments where these tools are load-bearing, and to know when a problem exceeds this domain and requires someone with deeper expertise.

Three sections sit under one domain because they share a reasoning framework and an assessment posture. Git is version control as the change ledger — the pre-commitment discipline from Domain 9 (Change Management Discipline), made mechanical. Containers are the operational layer that Domain 6 (Compute Architecture) introduced conceptually; this domain owns the operations. Kubernetes is the reconciliation loop in practice — the pod-as-cattle mindset shift from Domain 6 (Compute Architecture) extended from concept into daily operations.

Domain 6 (Compute Architecture) owns the conceptual layer: isolation tradeoffs, the supply chain problem, the VM-as-special versus pod-as-cattle mindset shift. This domain does not repeat that content — it cross-references it and builds on it. Domain 9 (Change Management Discipline) owns the change management process; this domain shows how Git makes parts of that process mechanical. Domain 1 (Scripting & Automation) owns the audit discipline for scripts; this domain transposes it to reading diffs and Dockerfiles.

The organizational-fit question — whether a given shop should adopt Kubernetes — is a real question, asked fresh each time. It was demoted to a neutral fit question in Domain 6 (Compute Architecture) as of v0.25, and this domain is likewise neutral: the cluster exists, operate it competently. The question of whether it should exist belongs to the adoption decision, not to the operational floor.

*The assessment bar is not "can build a Kubernetes cluster." It is: given an environment where Git, containers, and Kubernetes are in use, can you operate without needing to hand off immediately, and do you know when the problem is beyond this domain and does require a platform engineer?*

## Reasoning Framework: The Reconciliation Loop as the Operational Contract

How it is normally taught: DevOps tools are presented as a vocabulary to memorize. Learn git commands, learn docker commands, learn kubectl commands. The implicit model is that fluency means knowing more commands and syntax, and that each tool is an imperative interface — you run a command, it does a thing.

What it is actually for: all three tools implement the same operational contract — the reconciliation loop. The declared state is the source of truth; the running state is a consequence that the system works to match. In Git, the repository is the change ledger: every modification is a commit with a message, a diff, and a history that constitutes the audit trail. In containers, the image is the source of truth: the running container is a disposable instance that can be killed and replaced from the image at any time. In Kubernetes, the desired state in the manifest is the contract: the controller observes reality, compares it to the declared state, and takes action to converge the two. The practitioner's job in all three is the same: modify the declared state, observe the running state, and let the system reconcile. You do not fix running instances; you fix the declaration.

What misuse looks like: treating the tools as imperative commands that act on running instances rather than as interfaces to declared state. SSHing into a running container to fix a configuration file — the fix is lost on the next restart because the image was not updated. This is the wrong-model failure mode from Domain 6 (Compute Architecture), encountered in practice. Manually deleting a pod to force a restart instead of fixing the deployment spec that produced the broken pod — the controller recreates the same broken pod from the same broken spec. Force-pushing to a shared branch to overwrite history — the change ledger no longer reflects what happened, and every developer who based work on the overwritten commits has a repository that diverges from reality. Each of these is the same failure: bypassing the declaration to act on the instance directly, then being surprised when the system reconciles back to the declared state and discards the direct intervention.

*The parallel to Domain 1 (Scripting & Automation) is explicit: the audit discipline that applies to scripts applies equally to diffs. Before applying a diff — whether a git merge, a kubectl apply, or a docker build — you should be able to describe what each change does and what the collective effect will be. The diff is the script; applying it is running it. The fact that it is a declarative change rather than an imperative script does not reduce the obligation to understand it before applying it.*

## Section 1: Git — Version Control as the Change Ledger

Git is the change ledger for infrastructure. Every modification to configuration, code, or manifests is a commit with an author, a timestamp, a message, and a diff. The history is the audit trail. This is the pre-commitment discipline from Domain 9 (Change Management Discipline), made mechanical: the commit message forces you to describe what you did, the diff forces you to review what changed, and the history provides the record that a change review process needs.

### The Operational Vocabulary

- clone — copy a repository from a remote. The starting point for working with any codebase or configuration repository.

- branch — create a divergent line of development. Changes on a branch do not affect the main branch until merged. This is the Git equivalent of a change window: you make your changes in isolation, verify them, and merge when ready.

- commit — record a set of changes to the repository with a message. The commit message is the change documentation. A good commit message says what changed and why — not just "fix" or "update."

- diff — show the difference between two states. git diff shows uncommitted changes. git diff --staged shows staged changes. git diff branch1..branch2 shows the difference between two branches. Reading a diff before committing or merging is the audit step.

- log — show the commit history. git log --oneline gives a compact view. git log -p shows the diff for each commit. git log --follow filename shows the history of a specific file.

- blame — show which commit last modified each line of a file. The diagnostic tool for understanding why a line is the way it is: git blame filename, then git show <commit-hash> to see the full context of the change that produced it.

### Reading a Diff Before Applying It

The diff is the script. Before applying a diff — whether through git merge, git apply, or kubectl apply — the practitioner should be able to describe what each change does and what the collective effect will be. This is the audit discipline from Domain 1 (Scripting & Automation), transposed: the candidate who runs a script without reading it is the same candidate who applies a diff without reading it.

The specific questions a diff review should answer: What files change? What lines are added and removed? Does the change do what the commit message says it does? Are there changes the commit message does not mention? Does the change touch anything beyond its stated scope — the scope-creep pattern from Domain 1 (Scripting & Automation)? Is anything destructive — a deletion, a permission change, a configuration removal — and if so, is it intentional and documented?

### Merge Conflicts

A merge conflict means two changes to the same lines were made independently and Git cannot reconcile them automatically. The conflict is not a bug — it is Git telling you that a human decision is required. The resolution is not "pick one side." It is: understand what both changes were trying to accomplish, produce a result that serves both intentions (or deliberately choose one over the other with reasoning), and verify the result before committing.

The failure mode: resolving a conflict by accepting one side without reading the other, producing a result that silently drops a change someone else made. The merge commit's diff should be reviewed before pushing — the same audit discipline applied to the resolution itself.

### Force-Push as a Destructive Operation

git push --force overwrites the remote branch history with the local history. It is destructive because it rewrites the change ledger. Any commits that existed on the remote but not in the local history are gone. Any developer who based work on those commits now has a repository that diverges from the remote. The audit trail that the change management discipline depends on is broken — the history no longer reflects what actually happened.

Force-push has a legitimate use: cleaning up a personal feature branch's history before merging. The misuse is force-pushing to a shared branch — especially main — where other people's work is based on the history being overwritten. The correct practice: never force-push to shared branches. If a force-push to a shared branch is genuinely needed (rare), coordinate with everyone who has work based on the branch first.

### Config-as-Code and GitOps at Literacy Level

Config-as-code means system configuration is stored in a Git repository, version-controlled, reviewed through diffs, and deployed through a pipeline. The benefits map directly to the change management discipline from Domain 9 (Change Management Discipline): every configuration change has an author, a timestamp, a reviewable diff, and a rollback path (git revert). The configuration is not a set of files on a server that someone edited directly — it is a versioned artifact with a history.

GitOps extends this to Kubernetes: the desired state of the cluster is stored in a Git repository, and a controller reconciles the cluster to match it. This is the reconciliation loop applied to the cluster itself — the Git repository is the source of truth, and the controller converges. At literacy level, the candidate should understand the concept: the repo is the declaration, the controller is the reconciler, and you change the cluster by committing to the repo, not by running kubectl apply directly. The specific tools that implement this pattern are vendor specifics that change; the concept is stable.

## Section 2: Containers (Operational)

Domain 6 (Compute Architecture) owns the conceptual layer: what containers are, the isolation tradeoff (shared kernel), the supply chain problem, and the pod-as-cattle mindset shift. This section does not repeat that content. It owns operations: the day-to-day work of building, running, inspecting, and debugging containers.

### Image vs. Container vs. Registry

Three terms that are frequently conflated and should not be:

- Image: a read-only template containing the application and its dependencies. The build artifact. Immutable once built. Identified by a name and a tag (e.g., nginx:1.25).

- Container: a running instance of an image. A process (or set of processes) on the host, isolated by namespaces and cgroups. Mutable while running, but changes to the running container's filesystem are ephemeral — they exist only in the container's writable layer and are discarded when the container is removed.

- Registry: a storage and distribution service for images. Docker Hub, a private Harbor instance, a cloud provider's registry. The registry is where images are pushed after building and pulled before running.

The relationship: you build an image, push it to a registry, pull it on a host, and run it as a container. The image is the source of truth; the container is a disposable instance. This is the reconciliation loop at the container level: you fix the image, not the running container.

The `docker` CLI is the most commonly encountered interface for these operations, and the commands below use it as the reference vocabulary. The concepts — the OCI image format, the container runtime, the registry protocol — are portable: `podman` and `nerdctl` provide compatible interfaces built on the same underlying standards. The commands are load-bearing as operational vocabulary; the concepts they express are what transfer across tools.

### The Operational Vocabulary

- docker build -t name:tag . — build an image from a Dockerfile in the current directory. The tag identifies the image.

- docker run -d -p 8080:80 name:tag — run a container from an image in detached mode, mapping host port 8080 to container port 80.

- docker ps — list running containers. docker ps -a includes stopped containers.

- docker images — list locally available images.

- docker inspect container_id — detailed information about a container: its configuration, network settings, mounted volumes, and state.

- docker logs container_id — the stdout/stderr output of the container's main process. docker logs -f follows in real time.

- docker exec -it container_id bash — open an interactive shell inside a running container. Useful for debugging, but changes made inside the running container are ephemeral.

### Reading a Dockerfile at Audit Level

A Dockerfile is a build specification. Reading it at audit level means answering: what does this image contain, what does it run as, and what is the attack surface? This is the audit discipline from Domain 1 (Scripting & Automation), applied to container builds.

The questions a Dockerfile review should answer:

- What base image is used? A broad base image (ubuntu, debian) includes a full OS and a large package set — a larger attack surface and more supply chain exposure. A minimal base image (alpine, distroless) includes less. Domain 6 (Compute Architecture) owns the supply chain argument; the audit question is whether the base image choice is appropriate for the workload.

- What user does the container run as? By default, many Dockerfiles run as root. Running as root inside the container is a security concern — Domain 6 (Compute Architecture) established that container root maps more closely to host root than most operators realize. A Dockerfile that creates a non-root user and switches to it (USER directive) is applying the principle of least privilege.

- What packages are installed? Each package is a supply chain dependency. Package installations that fetch from the internet at build time (apt-get install, apk add) produce images whose contents depend on what was available at build time — the same Dockerfile may produce different images on different days.

- What is the entrypoint (ENTRYPOINT/CMD)? This is what runs when the container starts. Understanding it is necessary for understanding what the container does.

- Are there secrets in the Dockerfile? Hardcoded credentials, API keys, or tokens baked into the image are the credential exposure pattern from Domain 1 (Scripting & Automation), made worse because the image is pushed to a registry and may be accessible to others.

### Volumes and the Ephemeral-Filesystem Reflex

The "wrong model" exercise in Domain 6 (Compute Architecture) established the core lesson: changes made to a running container's filesystem are ephemeral. They exist only in the container's writable layer and are discarded when the container is removed or replaced. The sysadmin who execs into a running container, edits a config file, and expects the change to persist is applying the VM reflex to a container.

This domain deepens that lesson to intervention level. The correct response when a containerized application needs a configuration change:

1. Identify where the configuration actually lives — in the image (baked in at build time), in a mounted volume, or in environment variables.
2. If the configuration is in the image: update the Dockerfile or the configuration source, rebuild the image, and redeploy.
3. If the configuration is in a mounted volume: update the file on the host or in the config source that populates the volume.
4. If the configuration is in environment variables: update the deployment spec or the config source that provides them.
5. Verify the change persisted by restarting the container and confirming the new configuration is in effect.

Volumes are the mechanism for persisting data outside the container's ephemeral filesystem. A volume mounts a directory from the host (or a named volume managed by the container runtime) into the container's filesystem. Data written to the volume persists across container restarts and removals. The intervention-level understanding: data that must survive container replacement goes in a volume; everything else is ephemeral by design.

## Section 3: Kubernetes (Operational)

This section covers operating an existing cluster, not building one. The cluster exists; the sysadmin's job is to deploy workloads to it, diagnose problems, and know when a problem is in the cluster's infrastructure rather than in the workloads running on it.

### The Reconciliation Loop in Practice

Kubernetes implements the reconciliation loop as its core operational model. You declare desired state — "I want three replicas of this pod running with this image and these resources" — in a manifest. The controller observes the current state, compares it to the declared desired state, and takes action to converge the two. If a pod crashes, the controller starts a new one. If a node fails, the controller reschedules its pods elsewhere. If you change the desired state (update the image tag in a deployment), the controller rolls out the change.

The operational implication: you do not fix pods. You fix the desired state — the deployment spec, the config map, the secret, the PVC — and the controller converges. A pod that is misbehaving because its spec is wrong will be recreated with the same wrong spec no matter how many times you delete it. The fix is in the declaration, not in the instance.

This extends the pod-as-cattle mindset shift from Domain 6 (Compute Architecture) into daily practice. Pods are disposable. You do not SSH into a pod to debug it the way you would SSH into a VM — you read its logs, describe its state, identify what in the desired state is producing the failure, and update the spec. The pod is a consequence of the spec; fix the spec.

The concepts in this section — the reconciliation loop, desired state, controllers, convergence — are stable. They will be correct regardless of which Kubernetes distribution or version is in use. The kubectl commands are load-bearing for operations: they are the interface through which the reasoning is expressed. What is not load-bearing is version-specific feature sets, provider-specific managed Kubernetes details, or the specifics of any particular distribution's extensions. The operational floor is the same across all of them: declare state, observe, reconcile.

### The Operational Vocabulary

- kubectl get pods — list pods in the current namespace. kubectl get pods -A lists across all namespaces. kubectl get deployments, kubectl get services, kubectl get pvc for other resource types.

- kubectl describe pod name — detailed information about a pod: its status, events, container states, and the most recent events that affected it. The primary diagnostic tool for a pod that is not running correctly.

- kubectl logs pod-name — the stdout/stderr of the pod's container. kubectl logs -f follows in real time. kubectl logs --previous shows logs from the previous (crashed) container instance — critical for diagnosing CrashLoopBackOff.

- kubectl get events — cluster events sorted by time. Shows scheduling decisions, pull failures, probe failures, and other events that explain why a pod is in a particular state.

- kubectl apply -f manifest.yaml — declare desired state from a file. The controller reconciles the cluster to match.

- kubectl edit deployment name — open the deployment spec in an editor and apply changes on save. A quick way to make targeted changes to desired state without writing a full manifest file.

### What a Deployment, Service, Ingress, and PVC Are

At literacy level, a candidate should understand what each of these resource types is and what role it plays:

- Deployment: declares the desired state for a set of identical pods — how many replicas, what image, what resources, what environment. The deployment controller creates and manages a ReplicaSet, which creates and manages the pods. You change the deployment spec; the controller handles the rest.

- Service: provides a stable network identity for a set of pods. Pods are ephemeral — they are created and destroyed, and their IP addresses change. A service gives them a stable IP and DNS name that does not change when pods are replaced. The service routes traffic to the pods behind it.

- Ingress: exposes the service to the outside world via HTTP/HTTPS routing. An ingress controller receives external traffic and routes it to services based on host or path rules. The ingress resource is the declaration; the ingress controller is the reconciler.

- PersistentVolumeClaim (PVC): a request for storage by a user. The PVC asks the cluster for a certain amount of storage with certain access modes. The cluster provisioner creates a PersistentVolume that satisfies the claim and binds it. The PVC is how workloads that need persistent storage request it — the pod mounts the PVC, and the data persists across pod restarts.

### Triage Patterns

The three failure modes a sysadmin operating a Kubernetes cluster will encounter most frequently:

**CrashLoopBackOff** — the container starts, crashes, and Kubernetes restarts it, repeatedly. The pod is not failing to be scheduled; it is failing to stay running. The diagnostic sequence: kubectl describe pod name to see the container's last state and restart count, then kubectl logs pod-name --previous to see the logs from the crashed instance. The root cause is almost always in the desired state: a missing environment variable, a misconfigured command, an application that crashes on startup because it cannot connect to a dependency. The fix is in the deployment spec, not in the running pod. Deleting the pod produces a new pod with the same spec that crashes the same way.

**ImagePullBackOff** — Kubernetes cannot pull the container image. The diagnostic: kubectl describe pod name shows the pull error in events. Common causes: the image tag is wrong or does not exist, the registry requires authentication that is not configured, the image name is misspelled. The fix is in the deployment spec — correct the image reference. This is not a cluster problem; it is a declaration problem.

**Pending (unschedulable)** — the pod cannot be scheduled onto any node. The diagnostic: kubectl describe pod name shows the scheduling failure in events. Common causes: insufficient resources on all nodes (the pod requests more CPU or memory than any node has available), no node matches a node selector or node affinity rule, no PersistentVolume is available to bind the PVC. The fix may be in the deployment spec (reduce resource requests, fix the node selector) or may be a cluster capacity problem (add nodes) that exceeds the MV floor.

### When the Answer Is "This Needs a Platform Engineer"

The boundary between the MV floor and platform engineering:

Within the MV floor — the sysadmin's operational scope:
- Deploying, updating, scaling, and rolling back workloads
- Triage of common workload failure modes (CrashLoopBackOff, ImagePullBackOff, pending pods)
- Reading and understanding existing manifests and specs
- Making targeted modifications to existing specs (change an image tag, adjust replicas, add an environment variable, mount a config map)

Beyond the MV floor — call a platform engineer:
- Cluster installation, upgrade, or version migration
- Control plane failures (API server, etcd, scheduler, controller manager)
- CNI and networking plugin issues (pods cannot reach each other, DNS resolution failures at the cluster level)
- Storage class and CSI driver configuration
- RBAC policy design and service account management
- Custom Resource Definitions and operator development
- Cluster-level performance tuning and capacity planning
- Node-level failures (NotReady nodes, kernel panics, container runtime issues)

The reasoning is not "these things are hard" — it is "these things are in the cluster's infrastructure, not in the workloads running on it." The MV floor covers operating workloads on a functioning cluster. When the cluster itself is the problem, the expertise required is different from the expertise required to operate workloads on it. A sysadmin who recognizes this boundary and calls for the right expertise is demonstrating Level 4 reasoning, not admitting defeat.

## Level Definitions for This Domain

| Level | Label | Work product | What it means |
| --- | --- | --- | --- |
| Level 1 | DevOps Literacy | A description of what a Dockerfile/kubectl output/git log shows | Can read a Dockerfile, a kubectl describe output, and a git log, and describe what each shows. Can identify what image a container is running, what a deployment's desired state is, and what a series of commits changed. Can navigate a repository and find the history of a specific file. |
| Level 2 | DevOps Audit | A risk assessment identifying why a container/pod/diff is problematic | Can identify why a container won't start, why a pod is in CrashLoopBackOff, and what a diff will do before applying it. Can read a Dockerfile at audit level: what does this image contain, what does it run as, what is the attack surface. Can identify a destructive git operation (force-push to a shared branch, hard reset) and explain why it is destructive. Can distinguish between a workload problem and a cluster problem. |
| Level 3 | DevOps Commission | A specification for a container build or deployment | Can specify a container build (a Dockerfile that meets stated requirements with appropriate base image, non-root user, and minimal attack surface), write a deployment spec (YAML that a third party could review and deploy), and write a meaningful commit message with a rollback plan. Can articulate what a change does, what it affects, and how to reverse it — the pre-commitment discipline from Domain 9 (Change Management Discipline), expressed through Git. |
| Level 4 | DevOps Adaptation | A triage decision or adaptation with escalation reasoning | Can triage a failing cluster with multiple simultaneous issues, identifying which are within the MV floor and which require a platform engineer. Can adapt a deployment to a different context (different namespace, different resource constraints, different image registry) safely and explain every line changed. Can reason about when a problem exceeds the functional floor and articulate what expertise is needed and why. |

## Assessment Exercises

### [LITERACY] Reading the Artifacts

*Candidate is given three artifacts: (1) a Dockerfile that uses node:18 as a base image, installs dependencies, copies application code, sets USER node, exposes port 3000, and runs npm start; (2) a kubectl describe pod output showing a pod in Running state with 2 restarts, a liveness probe configured on /healthz port 3000, and recent events showing "Liveness probe failed: HTTP probe failed with status code 503"; (3) a git log showing five commits, the most recent with the message "increase liveness probe timeout" and a diff that changes timeoutSeconds from 1 to 5. Candidate must describe what each artifact shows and what the relationship between them might be.*

**Watch for:** Candidates who read each artifact in isolation without connecting them. The artifacts tell a story: the application (Dockerfile) runs on port 3000 with a health check endpoint; the pod is restarting because the liveness probe is failing (kubectl describe); the most recent commit increased the probe timeout, which is the intervention someone made to address the probe failures. A candidate who can connect the three artifacts into a coherent narrative is demonstrating Level 1 competence. Candidates who describe the Dockerfile without noting the non-root user, or who read the kubectl describe without identifying the liveness probe failure as the cause of the restarts, are reading without comprehension.

### [AUDIT] The Diff Before Applying

*Candidate is given a git diff for a Kubernetes deployment YAML. The diff makes three changes: (1) changes replicas from 3 to 1, (2) removes the livenessProbe section entirely, (3) changes the image tag from v1.2.3 to v1.2.4. The commit message says "update image to v1.2.4." Candidate must describe what the diff will actually do when applied, identify anything the commit message does not mention, and assess the risk of each change.*

**Watch for:** Candidates who read only the image tag change because that is what the commit message mentions. The diff does three things, not one. Reducing replicas from 3 to 1 is a capacity change that removes the redundancy the deployment provided — if the single remaining pod fails, the application is down until the controller starts a new one. Removing the liveness probe means Kubernetes will no longer detect and restart a container that is running but not responding — the pod will stay in Running state even if the application is hung. The commit message mentions only the image update; the other two changes are undocumented. This is the scope-creep pattern from Domain 1 (Scripting & Automation), transposed to infrastructure diffs: the change does more than it says, and the parts it does not mention are the ones most likely to cause an incident. A candidate who identifies all three changes and flags the undocumented ones is demonstrating Level 2 audit competence.

### [TRIAGE] The Pod in CrashLoopBackOff

*A pod is in CrashLoopBackOff. kubectl describe pod shows: Restart Count: 7, Last State: Terminated with exit code 1, Reason: Error. kubectl logs --previous shows: "Error: DATABASE_URL environment variable is not set." The deployment spec does not include a DATABASE_URL environment variable. Candidate must describe the diagnostic sequence they would follow, identify the root cause, and describe the fix.*

**Watch for:** Candidates who suggest deleting the pod to force a restart. The pod is already being restarted — that is what CrashLoopBackOff means. Deleting it produces a new pod with the same spec that crashes the same way. The root cause is in the desired state: the deployment spec is missing the DATABASE_URL environment variable, and the application crashes on startup because it cannot read a required configuration. The fix is to add the environment variable to the deployment spec (kubectl edit deployment or update the manifest and kubectl apply), not to intervene in the running pod. Candidates who identify that the fix is in the declaration, not the instance, are demonstrating the reconciliation loop reasoning. Candidates who suggest execing into the pod to set the environment variable are applying the VM reflex to a container — the wrong-model failure mode from Domain 6 (Compute Architecture), encountered in practice.

### [COMMISSION] The Deployment Spec

*Candidate must write a Kubernetes deployment spec for a web application with the following requirements: 3 replicas, the image myregistry.example.com/webapp:v2.1.0, resource limits of 256Mi memory and 500m CPU, a liveness probe on HTTP path /healthz port 8080, and a config map mounted as a volume at /etc/webapp/config. The spec should be complete enough that a third party could review it and deploy it without asking additional questions.*

**Watch for:** Specifications that omit the resource limits (the pod will be scheduled but may starve other workloads or be killed under pressure), that omit the liveness probe (Kubernetes cannot detect a hung container), or that mount the config map without specifying both the volume and the volumeMount (the mount will not work). A complete spec includes the apiVersion, kind, metadata, and spec with replicas, selector, template (with labels, containers, resources, livenessProbe, volumeMounts), and volumes. The exercise tests whether the candidate can produce a commission artifact — a specification that directs production work and can be evaluated by a reviewer. Candidates who produce a spec with the right structure but missing the safety-relevant details (resources, probes) are at Level 2, not Level 3 — they can read and audit but cannot yet specify with the completeness that production work requires.

### [ADAPTATION] The Failing Cluster

*A Kubernetes cluster has three simultaneous problems: (1) a pod in the web namespace is in CrashLoopBackOff — kubectl logs --previous shows "connection refused" to a database host that no longer resolves; (2) a PVC in the data namespace is stuck in Pending — kubectl get events shows "no persistent volumes available for claim" and "storageclass not found"; (3) two of five nodes are showing NotReady — kubectl describe node shows "Kubelet stopped posting node status." Candidate must triage all three, identify which are within the MV floor to address and which require a platform engineer, and describe the order in which they would address them.*

**Watch for:** Candidates who attempt to fix all three themselves. Problem 1 is within the MV floor — the pod is crashing because its database connection configuration is wrong, and the fix is in the deployment spec or config map. Problem 2 is at the boundary — the storage class does not exist, which may be a configuration error in the PVC (fixable) or a missing storage class on the cluster (needs a platform engineer to provision). Problem 3 is beyond the MV floor — nodes showing NotReady because the kubelet is not posting status is a cluster infrastructure problem that requires platform engineering expertise. The triage order matters: the NotReady nodes may be causing the PVC and scheduling problems, so the node issue should be escalated first. A candidate who articulates the boundary between workload problems and cluster problems, identifies which problems are symptoms of other problems, and calls for the right expertise at the right time is demonstrating Level 4 adaptation. The rubric rewards the candidate's ability to articulate what is within their operational authority and what is not — not their ability to fix everything. A candidate who tries to debug the kubelet on a NotReady node is overstepping the MV floor and may make the situation worse.
