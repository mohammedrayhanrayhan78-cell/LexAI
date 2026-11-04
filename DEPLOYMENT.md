# Deployment Guide: LexAI on a Production VPS with Docker

This guide outlines the steps required to deploy LexAI to a production-ready Virtual Private Server (VPS) running Ubuntu Server with Docker and Docker Compose.

---

## Prerequisites

1. A provisioned VPS (e.g., AWS EC2, DigitalOcean Droplet, Linode) running Ubuntu 22.04+ with at least **2 vCPUs and 4GB RAM**.
2. **Docker** and **Docker Compose** installed on the server.
3. A configured domain name pointing to your server's public IP address.

---

## Step 1: Clone Repository & Configure Environment

1. Clone the project repository onto your production server:
   ```bash
   git clone [https://github.com/your-org/legal-ai-assistant.git](https://github.com/your-org/legal-ai-assistant.git)
   cd legal-ai-assistant