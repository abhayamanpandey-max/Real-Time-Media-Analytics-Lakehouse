# AWS EC2 Ingestion Host Setup Guide

This guide details the step-by-step procedure for deploying the continuous ingestion stack (Kafka + Synthetic Event Producer + FastAPI Mock API) on an AWS EC2 instance.

---

> [!CAUTION]
> ### 🚨 CRITICAL COST & RESOURCE NOTICE
> This EC2 instance runs on a **4-month AWS credit allocation** (not a permanent free tier).
> 1. **Set an AWS Budgets Billing Alarm** (e.g. $5.00 threshold) immediately after provisioning to avoid unexpected charges.
> 2. **Tear down / terminate the EC2 instance** as soon as the project is evaluated or demoed. Do NOT leave it running indefinitely.

---

## 🏛️ Architecture Overview

The EC2 instance hosts the exact same Docker Compose stack that runs locally during dev testing:

```
[ Synthetic Generator (Container) ] ──> [ Kafka KRaft (Container) ] ──> [ FastAPI Mock API (Container: 0.0.0.0:8000) ]
                                                                                  │
                                                                       Public HTTP Port 8000
                                                                                  │
                                                                       ▼
                                                       [ Databricks Workflows Ingestion Job ]
```

---

## 📋 Step 1: Launch EC2 Instance

1. Log into **AWS Management Console** → Navigate to **EC2** → Click **Launch Instance**.
2. **Name**: `lakehouse-ingestion-host`
3. **AMI**: `Ubuntu Server 24.04 LTS` (or Amazon Linux 2023).
4. **Instance Type**: `t3.small` (2 vCPU, 2 GB RAM recommended for Kafka + Python containers) or `t3.micro`.
5. **Key Pair**: Select or create an SSH key pair (`lakehouse-ec2.pem`).
6. **Storage**: 20 GB gp3 root volume.

---

## 🔒 Step 2: Configure Security Group (Inbound Rules)

Create a Security Group named `lakehouse-ingestion-sg` with the following inbound rules:

| Type | Protocol | Port Range | Source | Purpose |
|------|----------|------------|--------|---------|
| SSH | TCP | 22 | My IP (`x.x.x.x/32`) | Secure terminal access |
| Custom TCP | TCP | 8000 | Anywhere (`0.0.0.0/0`) | Mock API accessible by Databricks |
| Custom TCP | TCP | 8080 | My IP (`x.x.x.x/32`) | Kafka UI web dashboard |

---

## ⚙️ Step 3: Install Docker & Docker Compose on Instance

SSH into your EC2 instance:

```bash
ssh -i "lakehouse-ec2.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Run the setup commands:

```bash
# Update packages and install Docker + Git
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git

# Add ubuntu user to docker group (no sudo required for docker)
sudo usermod -aG docker ubuntu
newgrp docker

# Verify installation
docker --version
docker compose version
```

---

## 🚀 Step 4: Clone Repository & Start Ingestion Stack

```bash
# Clone the repository
git clone https://github.com/abhayamanpandey-max/Real-Time-Media-Analytics-Lakehouse.git
cd Real-Time-Media-Analytics-Lakehouse

# Build and start all 4 containers (Kafka, Generator, Mock API, Kafka UI)
docker compose -f docker/docker-compose.yml up -d --build

# Verify all containers are healthy
docker compose -f docker/docker-compose.yml ps
```

---

## 🧪 Step 5: Test External Accessibility

From your local machine or browser, verify the endpoints:

```bash
# Health check endpoint (returns HTTP 200 OK)
curl http://<YOUR_EC2_PUBLIC_IP>:8000/health

# Event count endpoint
curl -H "Authorization: Bearer dev-bearer-token-local" http://<YOUR_EC2_PUBLIC_IP>:8000/events/count
```

---

## 🔗 Step 6: Connect Databricks Ingestion to EC2

1. Open `config/dev.yml` in your repository.
2. Update `api.base_url` to point to your EC2 public IP:
   ```yaml
   api:
     base_url: "http://<YOUR_EC2_PUBLIC_IP>:8000"
   ```
3. Or pass `API_BASE_URL=http://<YOUR_EC2_PUBLIC_IP>:8000` as an environment variable in your Databricks Workflow Job settings.

---

## 🛑 Step 7: Post-Evaluation Teardown

Once you have completed your evaluation or project demonstration:

```bash
# SSH into EC2 and stop containers
docker compose -f docker/docker-compose.yml down -v
```

Then in **AWS Console**:
- Select `lakehouse-ingestion-host` → **Instance State** → **Terminate Instance**.
