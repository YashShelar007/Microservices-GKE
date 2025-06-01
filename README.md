# Containerized Microservices on GKE

**Tech Stack:**

- Python 3.11 + Flask
- Docker
- Google Kubernetes Engine (GKE)
- Google Container Registry (GCR)
- Cloud Build (CI)
- Horizontal Pod Autoscaler (HPA)
- GCE Ingress (Load Balancer)

---

## Folder Structure

```

microservices-gke/
│
├── user-service/             # Flask code + Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── order-service/            # Flask code + Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── k8s/                      # Kubernetes manifests
│   ├── user-deployment.yaml
│   ├── order-deployment.yaml
│   ├── user-service.yaml
│   ├── order-service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
│
├── cloudbuild.yaml           # CI pipeline for building & deploying
└── README.md

```

---

## Features

1. **Two Flask Microservices**

   - `/users` → returns `["alice", "bob", "carol"]`
   - `/orders` → returns a static list of order objects  
     Both services run on port 8080 inside a container.

2. **Containerization & Registry**

   - Dockerfiles build each service into images:
     - `gcr.io/$PROJECT_ID/user-service:v1`
     - `gcr.io/$PROJECT_ID/order-service:v1`  
       Replace `$PROJECT_ID` with your actual GCP project ID (e.g. `my-gke-microservices`).
   - Pushed to Google Container Registry (GCR).

3. **Google Kubernetes Engine**

   - Created a 2-node GKE cluster (`microservices-cluster` in `us-central1-a`).
   - Deployed services via Kubernetes Deployments & Services.
   - **CPU Requests** (100 mCPU) in each Deployment so HPA can calculate CPU%:
     ```yaml
     resources:
       requests:
         cpu: 100m
     ```
   - Health checks (Liveness & Readiness) configured under `/users` and `/orders`.

4. **Ingress & Load Balancing**

   - A single GCE Ingress routes:
     - `/users` → `user-service`
     - `/orders` → `order-service`
   - External IP is automatically provisioned by GKE.

5. **Autoscaling**

   - Two HPAs scale `user-deployment` and `order-deployment` from 2 to 5 replicas based on CPU ≥ 50%.
   - **Tip:** If `kubectl get hpa` still shows `cpu: <unknown>/50%`, install Metrics Server:
     ```bash
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
     ```

6. **CI/CD with Cloud Build**
   - `cloudbuild.yaml` builds Docker images on every commit, pushes to GCR, and runs `kubectl apply` to update Deployments with a unique image tag.
   - Local builds tag with `v1`, but Cloud Build tags with `$BUILD_ID` (or `$SHORT_SHA` when Git-triggered) so each commit yields a new image.

---

## Deployment Steps

### 1. Prerequisites

- A GCP project (`YOUR_PROJECT_ID`) with Billing enabled.
  > Replace `YOUR_PROJECT_ID` below with your actual project ID (e.g. `my-gke-microservices`).
- Enabled APIs:

  - Container Registry (`containerregistry.googleapis.com`)
  - Container Engine (`container.googleapis.com`)
  - Cloud Build (`cloudbuild.googleapis.com`)
  - IAM (`iam.googleapis.com`)

- Installed and authenticated gcloud CLI:
  ```bash
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```

---

### 2. Build & Push Docker Images

1. Authenticate Docker to GCR:

   ```bash
   gcloud auth configure-docker
   ```

2. Build & push `user-service` (tag `v1` locally):

   ```bash
   docker build -t gcr.io/$PROJECT_ID/user-service:v1 ./user-service
   docker push gcr.io/$PROJECT_ID/user-service:v1
   ```

3. Build & push `order-service` (tag `v1` locally):

   ```bash
   docker build -t gcr.io/$PROJECT_ID/order-service:v1 ./order-service
   docker push gcr.io/$PROJECT_ID/order-service:v1
   ```

---

### 3. Create GKE Cluster

```bash
export PROJECT_ID=YOUR_PROJECT_ID
export CLUSTER_NAME=microservices-cluster
export ZONE=us-central1-a

gcloud config set project $PROJECT_ID

gcloud container clusters create $CLUSTER_NAME \
  --zone=$ZONE \
  --num-nodes=2 \
  --machine-type=n1-standard-1

gcloud container clusters get-credentials $CLUSTER_NAME --zone $ZONE
```

---

### 4. Deploy to GKE

```bash
kubectl apply -f k8s/user-deployment.yaml
kubectl apply -f k8s/user-service.yaml

kubectl apply -f k8s/order-deployment.yaml
kubectl apply -f k8s/order-service.yaml

kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

Wait for Ingress to get an external IP:

```bash
kubectl get ingress microservices-ingress -w
```

When you see an `ADDRESS` assigned (e.g. `34.123.45.67`), test:

```bash
curl http://34.123.45.67/users
curl http://34.123.45.67/orders
```

---

### 5. Enable Autoscaling

Verify HPA can see CPU percentages:

```bash
kubectl get hpa
```

You should see something like:

```
NAME        REFERENCE                     TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
user-hpa    Deployment/user-deployment    cpu: 2%/50%   2         5         2          10m
order-hpa   Deployment/order-deployment   cpu: 1%/50%   2         5         2          10m
```

To drive scaling, run a heavier load (for example, 2,000 requests with 50 concurrent clients):

```bash
hey -n 2000 -c 50 http://34.123.45.67/users
```

Watch HPA:

```bash
kubectl get hpa -w
```

You’ll see `REPLICAS` increase (2 → 3 → … up to 5) as CPU usage exceeds 50%, then scale back to 2 when load subsides.

---

### 6. CI/CD with Cloud Build

1. **Grant Cloud Build Service Account Permissions**
   In IAM & Admin → IAM, grant `PROJECT_NUMBER@cloudbuild.gserviceaccount.com` these roles:

   - Storage Admin (`roles/storage.admin`)
   - Kubernetes Engine Developer (`roles/container.developer`)
   - Kubernetes Engine Cluster Viewer (`roles/container.clusterViewer`)

2. **Test with a Manual Build** (tags images with `$BUILD_ID`):

   ```bash
   gcloud builds submit --config=cloudbuild.yaml \
     --substitutions=_CLUSTER_NAME="microservices-cluster",_ZONE="us-central1-a"
   ```

   - This builds/pushes two images tagged `gcr.io/$PROJECT_ID/user-service:$BUILD_ID` and `.../order-service:$BUILD_ID`, then updates deployments.

3. **Automate via Git Trigger**
   In the Cloud Build console → Triggers → “Create Trigger”:

   - Connect to your GitHub repo.
   - Trigger on push to `main`.
   - Select **cloudbuild.yaml**.

   Now every push to `main` runs the same steps (using `$SHORT_SHA` as the tag if Git-triggered).

---

## Architecture Diagram (Optional)

```
           ┌─────────────────────────────┐
           │     External Clients        │
           │ [curl, browser, Postman]    │
           └────────────┬────────────────┘
                        │
           ┌────────────▼─────────────┐
           │   GKE Ingress (GCE LB)   │
           │ routes /users → user-svc │
           │       /orders → order-svc│
           └────────────┬─────────────┘
                        │
       ┌────────────────▼─────────────────┐
       │        user-service (port 80)    │
       │ Replicas: 2 → HPA (2–5 pods)     │
       └────────────────┬─────────────────┘
                        │
       ┌────────────────▼─────────────────┐
       │        order-service (port 80)   │
       │ Replicas: 2 → HPA (2–5 pods)     │
       └────────────────┬─────────────────┘
                        │
           ┌────────────▼────────────────┐
           │  Google Kubernetes Engine   │
           │ (2 × n1-standard-1 nodes)   │
           └─────────────────────────────┘
```

---
