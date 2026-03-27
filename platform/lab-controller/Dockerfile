# Lab Controller — PowerShell + Python 3.11
#
# Base image: PowerShell Core on Ubuntu (needed for WinRM via PSWSMan).
# Python is added on top to run the FastAPI application.
#
# Build context: platform/lab-controller/
# Run: uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# Required env vars at runtime (supply via k8s Secret):
#   CONTROLLER_API_KEY       — shared secret checked on every request
#   HYPERV_HOST              — Hyper-V cluster hostname or IP
#   HYPERV_USERNAME          — UPN format: svc_claude@ad.hraedon.com
#   HYPERV_PASSWORD          — Hyper-V service account password
#   HYPERV_GUEST_USERNAME    — Guest domain admin (ad.labdomain.dev\claude)
#   HYPERV_GUEST_PASSWORD    — Guest domain admin password
#   GUACAMOLE_URL            — http://guacamole-service/guacamole
#   GUACAMOLE_USERNAME       — Guacamole API admin username
#   GUACAMOLE_PASSWORD       — Guacamole API admin password

FROM mcr.microsoft.com/powershell:7.4-ubuntu-22.04

# ----- System deps -----
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Use python3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# ----- PSWSMan: WinRM for Linux PowerShell -----
# PSWSMan replaces the Windows WinRM client stack for non-Windows PowerShell Core.
# Must be installed before Invoke-Command -ComputerName will work against Windows hosts.
RUN pwsh -NoProfile -NonInteractive -Command \
    "Install-Module -Name PSWSMan -Scope AllUsers -Force -AcceptLicense; \
     Install-WSMan"

# ----- Python app -----
WORKDIR /app

# Copy scenarios from project root context
COPY scenarios /scenarios

COPY platform/lab-controller/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY platform/lab-controller/app/ ./app/
COPY platform/lab-controller/environments.yaml .

# SQLite DB lives in /data so it can be backed by a k8s PersistentVolume.
# The app uses ./lab_state.db by default; override via SQLALCHEMY_DATABASE_URL
# or mount a PV at /data and set: SQLALCHEMY_DATABASE_URL=sqlite:////data/lab_state.db
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
