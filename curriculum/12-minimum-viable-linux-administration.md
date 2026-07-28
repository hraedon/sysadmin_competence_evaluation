---
domain: 12
id: minimum-viable-linux-administration
title: "Minimum Viable Linux Administration"
subtitle: "Not Linux expertise — the functional floor for operating in environments you will actually encounter"
reviewed: 2026-07-10
---

# Domain 12: Minimum Viable Linux Administration

*Not Linux expertise — the functional floor for operating in environments you will actually encounter*

## Scope and Framing

Linux is not a single operating system. It is a family of distributions sharing a kernel lineage and a philosophical approach, with different package managers, different default configurations, different file locations for the same services, and different support lifecycles. The sysadmin who treats Linux as a monolith will be repeatedly surprised. The sysadmin who understands the common substrate and the ways distributions diverge from it has a durable foundation.

This domain targets the minimum functional capability required to operate in Linux environments without being a Linux specialist. The specific contexts a sysadmin encounters Linux: container base images and the debugging that requires, network appliances and embedded Linux with restricted shells, monitoring agents and infrastructure tooling that ships as Linux services, cloud VMs that need to be provisioned and left in a known state, and the occasional on-premises Linux server that nobody wants to touch. In all of these contexts, the goal is the same: find what you need, understand what you're looking at, make a targeted change, and verify it worked.

*The assessment bar is not 'can administer a Linux system.' It is: given a Linux system in a context a sysadmin will actually encounter, can you operate without needing to hand off immediately, and do you know when the problem is beyond this domain and does require a Linux specialist?*

## Reasoning Framework: Unix Philosophy as Composition Model

How it is normally taught: Linux commands are presented as a vocabulary to memorize. Learn ls, learn grep, learn find, learn pipes. The implicit model is that fluency means knowing more commands.

What it is actually for: the Unix philosophy — small tools that do one thing well, connected through pipes — means that a command pipeline is understandable by reading each component independently. The output of one command becomes the input of the next. A candidate who understands this model can reason about an unfamiliar pipeline by identifying each stage rather than recognizing the whole incantation.

What misuse looks like: treating a shell one-liner as an opaque incantation, copying it from Stack Overflow, and running it without understanding what each pipe stage does. This is the Domain 1 script audit failure transposed to the shell: the candidate who runs a command they do not understand is the same candidate who runs a script they have not read. On a production Linux system, this produces the same class of failures.

*The parallel to Domain 1 is explicit and worth naming to the learner: the commission-audit discipline that applies to PowerShell scripts applies equally to shell one-liners. Before running a pipeline you did not write, you should be able to describe what each stage does and what the collective output will be. The fact that it is a one-liner rather than a script does not reduce the obligation to understand it.*

## Distributions: The Family, Not the Monolith

### Why Distributions Diverge and Why It Matters

Every mainstream Linux distribution shares a kernel and a set of GNU userland utilities. Beyond that, they diverge in ways that produce predictable confusion for someone who learned on one and is operating on another.

- Package management: Debian-family distributions (Ubuntu, Debian, Linux Mint) use apt. Red Hat-family distributions (RHEL, Fedora, Rocky Linux, AlmaLinux) use dnf or yum. SUSE uses zypper. Alpine uses apk. The commands for installing, updating, and removing packages are different. The locations where packages install their files may differ. The candidate who types apt install on a RHEL system will get an error they did not expect.

- Default service configurations: the same service may have different default configuration file locations, different default enabled features, and different default security postures across distributions. Apache on Debian and Apache on RHEL are configured differently by default. The candidate who knows where to look on one distribution may look in the wrong place on another.

- Init system: systemd has largely won but the transition was not instantaneous and some environments still run older init systems. More practically, the way systemd is configured varies between distributions in subtle ways.

### Support Lifecycle Risk: The CentOS Lesson

CentOS is the canonical example: organizations built production infrastructure on what they understood to be a stable free RHEL rebuild, Red Hat changed the terms, and the resulting unplanned migrations revealed how completely the lifecycle risk had been ignored at deployment time. Rocky Linux and AlmaLinux emerged as replacements, but the lesson is not specific to CentOS.

Before deploying any Linux distribution in production: understand who controls the release lifecycle, what the support timeline is, and what happens to the distribution if the controlling organization changes direction. Pure community distributions (Debian, Ubuntu LTS) have different lifecycle risk profiles than distributions downstream of a commercial product. Neither is necessarily wrong — but the risk should be understood before the deployment, not discovered when end-of-life is announced.

## The Filesystem Hierarchy: Where Things Live

Linux has a standardized filesystem hierarchy. A Windows sysadmin who knows this map saves hours of searching. A Windows sysadmin who does not will look for configuration files in the wrong places, write data to inappropriate locations, and be confused when log files appear somewhere they did not expect.

- /etc — system-wide configuration files. This is where you look when you need to change how a service behaves. /etc/ssh/sshd_config, /etc/nginx/nginx.conf, /etc/systemd/system — all here.

- /var — variable data: logs in /var/log, spool files, package manager databases, application state that changes over time. This is where you look when you need to read logs.

- /home — user home directories. Each user's personal files, shell configuration, SSH keys.

- /opt — third-party software installed outside the standard package manager. Vendor-installed software often lands here.

- /usr — installed software and its support files. /usr/bin for user binaries, /usr/lib for libraries. Distinguished from /bin and /lib which are for essential system utilities.

- /tmp — temporary files with automatic cleanup. Files here do not persist across reboots on most distributions. Do not use this for anything you want to keep.

- /proc and /sys — virtual filesystems that expose kernel and hardware state. Not disk storage. Reading from /proc/meminfo gives current memory statistics; reading /proc/cpuinfo gives CPU details. Useful for diagnostics.

## Editors: The Vim Survival Vocabulary and the Case for Nano

Vim is the editor that will be available on essentially every Linux system, including minimal installs, network appliances with restricted package sets, and recovery environments. The reason it persists despite a learning curve that has defeated experienced professionals is that it is genuinely powerful once learned and genuinely available everywhere.

The culture that treats vim fluency as a professional marker is doing the same thing as the culture that treats memorizing port numbers as evidence of competence — confusing familiarity with the tool for understanding of the underlying problem. A sysadmin who can triage a system quickly with nano is more useful in a crisis than one who is still trying to remember how to navigate vim. The goal is to have working knowledge of both: nano because it is immediately usable and produces less distress, vim because it is inescapable.

### Vim Survival Vocabulary

- vim filename — open a file. If the file does not exist, vim will create it on save.

- i — enter insert mode. In insert mode, typing enters text. This is not the default mode.

- Escape — return to normal mode. When in doubt, press Escape.

- :wq — save (write) and quit. Only works in normal mode.

- :q! — quit without saving. The exclamation mark overrides the protest that unsaved changes exist.

- :w — save without quitting.

- The single most important vim fact: vim starts in normal mode where keypresses are commands, not text entry. Every vim horror story begins with someone typing without pressing i first and not understanding why their keystrokes are doing strange things.

### Nano: The Friendlier Alternative

Nano displays its key bindings at the bottom of the screen. Ctrl+O saves, Ctrl+X exits. It behaves the way a text editor is expected to behave. When nano is available, use it. When it is not available — minimal container images, appliance shells, recovery environments — vim is what you have.

## Package Management and System Hygiene

Package management on Linux is the equivalent of Windows Update plus application installation plus driver management, unified into a single system that handles dependency resolution automatically. Understanding the basics is required for two reasons: installing tools you need, and keeping the system patched.

- Debian/Ubuntu — apt update refreshes the package list. apt upgrade installs available updates. apt install packagename installs a package. apt remove packagename removes a package. sudo is required for all of these.

- RHEL/Fedora/Rocky — dnf update updates all packages. dnf install packagename installs a package. On older RHEL systems, yum is the equivalent.

- The security connection: a Linux system that has not been patched is accumulating CVEs exactly as a Windows system does. The absence of a Windows Update notification does not mean the system is current. Checking when a system last received updates — and whether unattended-upgrades or dnf-automatic is configured — is a basic hygiene step when inheriting a Linux system.

## Permissions: The Execute Bit and the Windows Sysadmin's Confusion

Linux file permissions are different enough from Windows that Windows sysadmins make predictable mistakes. The most common: copying a script to a Linux system and wondering why it will not run. The execute bit.

Linux permissions are expressed as three groups of three bits: owner, group, and other. Each group has read (r), write (w), and execute (x) bits. A file with permissions -rw-r--r-- can be read by everyone but executed by nobody. chmod +x filename adds the execute bit for all. chmod 755 filename sets the common pattern for executable scripts: owner can read/write/execute, everyone else can read/execute.

- ls -la shows permissions, owner, group, size, and modification time for all files including hidden ones (starting with .).

- The execute bit on a directory means something different than on a file: it means you can enter the directory and access its contents.

- chown user:group filename changes ownership. This requires sudo if you are not the current owner.

- The specific footgun: a script that works when run as root but fails when run with sudo because sudo resets the PATH to a minimal set that does not include the directories where your tools are installed. sudo -E preserves the environment. sudo visudo can add specific PATH exceptions.

## Storage: LVM and the Partition Trap

A Windows sysadmin provisioning storage on Linux for the first time will reach for familiar patterns: create partitions on the disk, format them, mount them. This works until you need to extend storage later and discover that the MBR partition table supports a maximum of four primary partitions, and you have already used them.

The extended/logical partition workaround exists but it is a second-class mechanism that creates its own complications. LVM (Logical Volume Manager) is the correct answer and the reason it exists is precisely this limitation.

### The LVM Mental Model

LVM introduces a layer of abstraction between physical disks and the filesystems that use them. Physical volumes (PVs) are raw disks or partitions. Volume groups (VGs) pool physical volumes into a single storage pool. Logical volumes (LVs) are carved from volume groups and are what you actually format and mount.

- The key benefit: logical volumes can be extended online without unmounting, by adding physical storage to the volume group and extending the logical volume. Growing a filesystem on a running production system without downtime is a standard LVM operation.

- pvcreate /dev/sdb — initialize a disk as a physical volume.

- vgextend vgname /dev/sdb — add the physical volume to an existing volume group.

- lvextend -L +50G /dev/vgname/lvname — extend a logical volume by 50GB.

- resize2fs /dev/vgname/lvname — extend the filesystem to fill the new space (ext4). xfs_growfs mountpoint — equivalent for XFS.

The failure mode of not using LVM: a system provisioned with four primary MBR partitions that needs a fifth partition. The options are all bad: reformat (data loss), use extended partitions (complication), or migrate to LVM after the fact (significant effort). The correct move is to use LVM from the beginning on any system where storage may need to grow.

## Service Management and the Stable System That Will Not Restart

### Systemctl Basics

Systemd is the init system on essentially every modern Linux distribution. Systemctl is the management interface.

- systemctl status servicename — current state of a service, last few log lines, whether it is enabled to start on boot.

- systemctl start/stop/restart servicename — start, stop, or restart a service.

- systemctl enable servicename — configure the service to start automatically on boot. Does not start it immediately.

- systemctl disable servicename — remove the automatic startup configuration.

- systemctl list-units --type=service — list all service units and their states.

The distinction between enable and start is one of the most common sources of confusion: a service can be running but not enabled (it will not survive a reboot), enabled but not running (it was configured to start but something prevented it), or both running and enabled (the normal desired state).

### The System That Never Restarts

A Linux system that has not been restarted in years is an untested restart. It is the backup you have never tested, the RAID array that has never experienced a rebuild. It will fail at the worst possible moment.

The specific failure modes that accumulate on systems that never restart: kernel patches that require a reboot to take effect, leaving the system running with vulnerabilities that are patched in the installed kernel but not yet active. Services that have been manually adjusted in ways that were never captured in systemd unit files — the adjustments work in the running process but will not survive a restart because they exist only in memory or in configuration that bypasses the startup mechanism. Dependencies between services that work when everything started in the right order years ago and will not work if the system restarts with services starting in a different order or with a service that was manually started after the fact now configured to start automatically.

*The correct practice: schedule periodic restart tests in a maintenance window. Not necessarily frequent reboots — the goal is to verify that the system comes back in a known state, not to maximize reboot frequency. A system that has been verified to restart cleanly is a maintained system. A system that has never been restarted is a system whose restart behavior is unknown, and unknown behavior in infrastructure is risk. Domain 10 established that an untested backup is functionally equivalent to no backup. The same principle applies here: an untested restart procedure is a failed restart procedure, discovered at the worst possible moment.*

## Security: SELinux and the Disable Instinct

SELinux (Security-Enhanced Linux) is a mandatory access control system that constrains what processes can do even when running as root. It implements the principle from Domain 8 (Security Reasoning): every process has a defined security context, and operations that exceed that context are denied regardless of traditional file permissions.

The reason administrators disable it is that SELinux denials produce error messages that do not clearly explain what was denied or why, and the tooling for diagnosing and fixing SELinux policy violations requires learning audit2allow and the SELinux policy framework. When an application fails because of SELinux, the fastest fix is setenforce 0 (temporary, until next reboot) or setting SELINUX=disabled in /etc/selinux/config (permanent). The application works. The security control is gone.

This is Domain 8's implicit risk acceptance pattern in a specific Linux context. The administrator has not decided that SELinux's protection is not worth the operational cost — they have decided to make the error go away, and disabling SELinux made the error go away. The security control was not evaluated. It was eliminated because it was inconvenient.

- The correct response to an SELinux denial: identify what was denied using audit2why or sealert, understand whether the denial represents a genuine security violation or an overly restrictive policy, and either fix the application to operate within its security context or write a targeted policy exception. This takes longer than setenforce 0. It produces a system that is both functional and secure.

- audit2why < /var/log/audit/audit.log — explains why a denial occurred in human-readable terms.

- sealert -a /var/log/audit/audit.log — more detailed analysis with suggested fixes.

- The tell that SELinux has been disabled for the wrong reasons: /etc/selinux/config shows SELINUX=disabled with no documentation for why. A responsible disable would be accompanied by documentation of what was evaluated and what compensating control was put in place.

## Process Management and Network Diagnostics

### What Is This System Actually Doing

A service that systemctl says is running but that is not responding requires looking at the process directly.

- ps aux — all running processes with CPU and memory usage, user, and command line. ps aux | grep servicename finds processes by name.

- top / htop — interactive process viewer. Sorts by CPU by default. M sorts by memory. htop is friendlier but may not be installed on minimal systems.

- kill PID — sends SIGTERM (polite shutdown request) to a process. kill -9 PID sends SIGKILL (immediate termination, cannot be caught or ignored).

- lsof -p PID — lists open files for a process, including network connections. Useful for a hung process: what file or socket is it waiting on?

- strace -p PID — traces system calls made by a running process. Powerful for diagnosing hangs and unexpected behavior. May not be installed by default.

### Network Diagnosis on Linux

The tooling that Windows sysadmins expect from ipconfig and netstat has moved. On modern Linux systems the replacements are ip and ss.

- ip addr — equivalent to ipconfig. Shows interfaces and their addresses.

- ip route — shows the routing table. ip route get 8.8.8.8 shows which route would be used to reach a specific destination.

- ss -tulnp — equivalent to netstat -an. Shows listening sockets with the process that owns them. t=TCP, u=UDP, l=listening, n=numeric (no name resolution), p=process.

- ifconfig and netstat are deprecated on modern distributions and may not be installed. Do not assume they are available.

- curl -v and wget are the tools for testing HTTP/HTTPS connectivity from the command line. curl -v https://destination shows the full request and response including certificate information.

## The CLI-First Culture and Cross-Platform Tooling

The infrastructure tooling industry has decided that graphical interfaces are optional and command-line interfaces are the serious practitioner's domain. This produces two related challenges for sysadmins coming from Windows environments.

The first: Microsoft and others have invested in cross-platform tooling — PowerShell runs on Linux, Azure CLI runs on Linux, many Windows management tools have Linux equivalents. This is genuinely useful for automation and for operators who are deeply fluent in those tools. It becomes a trap when it substitutes for learning the native idioms of the platform. A sysadmin who manages Linux systems exclusively through PowerShell will be slower than one who knows the native tools, will produce code that is harder for Linux-native administrators to read and maintain, and will be confused when documentation and error messages assume native tooling.

The correct posture: use cross-platform tooling for automation and for tasks where your existing fluency provides genuine productivity. Learn the native tools for diagnosis, triage, and ad-hoc operations. The overlap is substantial — you can write PowerShell scripts that orchestrate native Linux tools, getting the fluency of PowerShell syntax while using the reliability of native commands.

## Logs: Journalctl and the Traditional Log Files

Modern Linux systems have two log destinations that coexist: the systemd journal (accessed via journalctl) and traditional log files in /var/log. Understanding both is necessary because different systems and different software use both.

- journalctl -u servicename — all journal entries for a specific service.

- journalctl -f — follow new journal entries in real time. Equivalent to tail -f for the system journal.

- journalctl --since '1 hour ago' — entries from the last hour. Accepts natural language time expressions.

- journalctl -b — entries from the current boot. journalctl -b -1 — entries from the previous boot. Useful for diagnosing what happened during a restart.

- /var/log/syslog or /var/log/messages — traditional system log. /var/log/auth.log or /var/log/secure — authentication events. /var/log/kern.log — kernel messages.

- tail -f /var/log/filename — follow a traditional log file in real time.

- grep 'pattern' /var/log/filename — search a log file for a specific pattern. grep -i is case-insensitive. grep -r searches recursively.

## SSH: Access and Common Failure Modes

SSH is the primary access mechanism for Linux systems. The failure modes are specific enough to be teachable and common enough to warrant explicit coverage.

- Connection refused: the SSH daemon is not running. systemctl status sshd on the target system (if you have another way to reach it) confirms this. If you cannot reach the system at all, this is the likely cause.

- Connection timed out: a firewall is blocking TCP 22. Check the firewall rules on the target system (iptables -L or firewall-cmd --list-all on RHEL-family) and any network-layer firewalls between you and the target.

- Permission denied (publickey): your key is not in the authorized_keys file on the target, or the permissions on ~/.ssh or ~/.ssh/authorized_keys are wrong. ~/.ssh must be 700. ~/.ssh/authorized_keys must be 600. If the permissions are wrong, SSH will ignore the file silently.

- Host key verification failed: the server's host key has changed (common after a system rebuild or IP reuse). If this is expected, remove the old entry with ssh-keygen -R hostname. If it is unexpected, investigate before connecting — this is what a man-in-the-middle attack looks like.

- ssh -v adds verbose output that shows exactly where in the authentication sequence the connection is failing. ssh -vvv is maximally verbose. These are the diagnostic tools for SSH problems.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Linux Navigation | Can find their way around a Linux filesystem, read files and logs, identify running services, and determine what distribution they are on. Can use vim well enough to open a file, make a change, and exit without restarting the computer. Can use nano without hesitation. |
| Level 2 | Linux Triage | Can diagnose a problem well enough to determine what is wrong and whether it is within their operational authority to fix. Can read systemd journal and traditional logs. Can inspect running processes and network state. Can determine whether a service is running, enabled, or failing to start. Can identify the package manager and whether the system is current on patches. |
| Level 3 | Linux Intervention | Can make targeted, understood changes: edit a configuration file and restart the affected service, install or remove a package, add a user and configure their access, extend a logical volume without taking the system offline, diagnose and address an SSH connectivity problem, investigate a failing SELinux denial rather than disabling SELinux. |
| Level 4 | Linux Maintenance | Can maintain a Linux system in a known state over time: manage patching, ensure services are configured to start correctly after restart, verify that configuration is captured in files rather than existing only in running state, manage LVM storage correctly, reason about distribution lifecycle risk. Can recognize when a system's undocumented accumulated state represents a maintenance liability and articulate what remediation would look like. |

## Assessment Exercises

### [LITERACY] The System You Just Inherited

*Candidate is given a Linux system they have never seen before. They must determine: what distribution it is, when it last received updates, what services are running and enabled, what storage volumes exist and their utilization, and what the last ten authentication events in the log show. They must do this using only the command line. List the specific commands you would run in order.*

**Watch for:** Candidates who cannot identify the commands for each piece of information, or who assume the distribution without checking. The exercise tests whether the candidate has the navigation vocabulary to orient themselves on an unfamiliar system. cat /etc/os-release for distribution, last reboot or uptime for restart history, dnf check-update or apt list --upgradable for patch state, systemctl list-units --type=service for services, df -h and lvs for storage, and journalctl or /var/log/auth.log for authentication events. A candidate who can produce this list in a reasonable order is demonstrating Level 1 competence.

### [TRIAGE] The Service That Will Not Start

*A monitoring alert shows that nginx is not responding on a Linux server. systemctl status nginx shows the service as inactive (dead). Candidate must describe the complete diagnostic sequence: what they check first, what the possible failure causes are, and what each check would tell them about the cause.*

**Watch for:** Candidates who immediately run systemctl restart nginx without first checking why the service is down. The correct diagnostic sequence: journalctl -u nginx -n 50 to see the last 50 log entries and why it stopped, then nginx -t to check configuration syntax if the logs suggest a configuration problem, then check listening ports with ss -tulnp to confirm whether nginx was running before the current state, then check disk space with df -h (a full /var/log partition is a common cause of service failure). Restarting before diagnosing may work but leaves the underlying cause unaddressed. A candidate who diagnoses before acting is demonstrating Level 2 reasoning.

### [INTERVENTION] The Disk That Is Almost Full

*A server is showing /var at 94% utilization. The disk uses LVM. The volume group has 200GB of unallocated space. Candidate must describe the exact sequence of commands to extend the /var logical volume online without unmounting it, including verification that each step succeeded before proceeding.*

**Watch for:** Candidates who describe creating a new partition rather than extending the logical volume, or who describe a sequence that would require unmounting /var (which is not possible on a running system with active logs). The correct sequence: lvextend -L +100G /dev/vgname/var, then resize2fs /dev/vgname/var (for ext4) or xfs_growfs /var (for XFS), then df -h /var to verify the extension took effect. The exercise tests LVM mental model: candidates who know that LVM enables online extension without unmounting are demonstrating Level 3 competence. Candidates who reach for partition tools are demonstrating the Windows-reflex-on-Linux failure mode.

### [INTERVENTION] The SELinux Denial

*A web application that was working yesterday is returning permission denied errors today. The application logs show it cannot write to /var/www/uploads. File permissions on that directory are 777. The application runs as the apache user which owns the directory. A junior team member has suggested running setenforce 0 to fix the problem. Candidate must explain why 777 permissions with correct ownership should be sufficient but apparently is not, why setenforce 0 is the wrong response, and what the correct diagnostic and remediation sequence is.*

**Watch for:** Candidates who approve setenforce 0 as a temporary fix 'while we investigate.' The candidate should recognize that 777 with correct ownership means traditional DAC permissions are not the issue — the constraint is SELinux MAC policy. setenforce 0 is never a temporary fix because it removes the security control entirely and the path back to enforcing mode requires fixing the underlying SELinux issue anyway. The correct sequence: check /var/log/audit/audit.log for AVC denials, run audit2why to understand what was denied, determine whether the denial represents a genuine security violation or a policy gap, and use chcon or semanage fcontext to apply the correct security context to /var/www/uploads if it is a policy gap.

### [SYNTHESIS] The Pipeline You Did Not Write

*Candidate is given the following command and must describe what each stage does, what the output will be, and whether it is safe to run on a production system:

  ps aux | grep -v grep | grep nginx | awk '{print $2}' | xargs kill -9*

**Watch for:** Candidates who either refuse to engage because they do not recognize the command, or who confirm it is safe without analyzing each stage. The pipeline: ps aux lists all processes, grep -v grep removes the grep process itself from the output (a common idiom), grep nginx filters for nginx processes, awk '{print $2}' extracts the PID column, xargs kill -9 sends SIGKILL to every extracted PID. This command will kill every process whose command line contains the string 'nginx' with SIGKILL — no graceful shutdown, no chance for the process to clean up open files or flush buffers. On a production system this is equivalent to pulling the power on the nginx process. The correct way to stop nginx is systemctl stop nginx which sends SIGTERM first and gives the process time to finish active connections. The exercise tests the commission-audit discipline from Domain 1 applied to shell pipelines.
