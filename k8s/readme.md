# Secure Customer Management API on Amazon EKS using IRSA and DynamoDB

## Project Overview

This project demonstrates how to securely access Amazon DynamoDB from applications running inside Amazon EKS (Elastic Kubernetes Service) using IAM Roles for Service Accounts (IRSA), without storing AWS Access Keys inside Kubernetes pods.

The application is a Flask-based Customer Management API that performs CRUD operations on a DynamoDB table and uses IAM-based authentication through IRSA for secure access.

---

# Problem Statement

Traditionally, applications running inside Kubernetes clusters access AWS services using static AWS credentials:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

This approach introduces several security risks:

* Long-lived credentials
* Secret leakage
* Credential rotation challenges
* Increased attack surface

This project solves the problem by using IRSA (IAM Roles for Service Accounts), which allows Kubernetes pods to securely assume IAM roles and obtain temporary AWS credentials from AWS STS.

---

# Project Objectives

* Deploy an application on Amazon EKS
* Store customer information in DynamoDB
* Access AWS services without AWS access keys
* Implement IAM Roles for Service Accounts (IRSA)
* Follow the Principle of Least Privilege
* Demonstrate secure cloud-native authentication

---

# Architecture

```text
                        AWS Cloud

 ┌──────────────────────────────┐
 │          DynamoDB            │
 │         customers            │
 └──────────────▲───────────────┘
                │
                │ IAM Policy
                │
 ┌──────────────┴───────────────┐
 │          IAM Role            │
 └──────────────▲───────────────┘
                │
              IRSA
                │
 ┌──────────────┴───────────────┐
 │ Kubernetes Service Account   │
 │      customer-api-sa         │
 └──────────────▲───────────────┘
                │
 ┌──────────────┴───────────────┐
 │      Flask Customer API      │
 │      Running on EKS          │
 └──────────────▲───────────────┘
                │
         Kubernetes Service
                │
              Client
```

---

# Technologies Used

## AWS Services

* Amazon EKS
* Amazon DynamoDB
* Amazon ECR
* IAM
* STS
* OIDC Provider

## Kubernetes

* Deployment
* Service
* Namespace
* Service Account

## Development

* Python
* Flask
* boto3
* Docker
* Gunicorn

---

# Project Structure

```text
customer-api/
│
├── app.py
├── requirements.txt
├── Dockerfile
│
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
│
└── README.md
```

---

# Prerequisites

Install:

* AWS CLI
* kubectl
* Docker
* eksctl
* Python 3
* Virtual Environment

Verify:

```bash
aws --version
kubectl version --client
docker --version
eksctl version
python3 --version
```

---

# Step 1 - Create DynamoDB Table

## Why?

The application needs a database to store customer information.

Create table:

```bash
aws dynamodb create-table \
  --table-name customers \
  --attribute-definitions \
      AttributeName=customer_id,AttributeType=S \
  --key-schema \
      AttributeName=customer_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Verify:

```bash
aws dynamodb describe-table \
  --table-name customers
```

---

# Step 2 - Create EKS Cluster

## Why?

IRSA only works with EKS because it integrates Kubernetes Service Accounts with IAM Roles.

Create cluster:

```bash
eksctl create cluster \
  --name customer-dynamodb-cluster \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t3.small \
  --nodes 1 \
  --managed
```

Verify:

```bash
kubectl get nodes
```

---

# Step 3 - Associate OIDC Provider

## Why?

OIDC allows AWS IAM to trust identities issued by Kubernetes Service Accounts.

Associate OIDC:

```bash
eksctl utils associate-iam-oidc-provider \
  --cluster customer-dynamodb-cluster \
  --region us-east-1 \
  --approve
```

Verify:

```bash
aws eks describe-cluster \
  --name customer-dynamodb-cluster \
  --region us-east-1 \
  --query "cluster.identity.oidc.issuer"
```

---

# Step 4 - Create IAM Policy

## Why?

IAM Policies define what actions are allowed on AWS resources.

Policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/customers"
    }
  ]
}
```

Create policy:

```bash
aws iam create-policy \
  --policy-name CustomerDynamoDBPolicy \
  --policy-document file://dynamodb-policy.json
```

---

# Step 5 - Create Namespace

```bash
kubectl create namespace customer-app
```

---

# Step 6 - Configure IRSA

## Why?

IRSA allows Kubernetes Pods to assume IAM Roles securely.

Create IAM Service Account:

```bash
eksctl create iamserviceaccount \
  --cluster customer-dynamodb-cluster \
  --region us-east-1 \
  --namespace customer-app \
  --name customer-api-sa \
  --attach-policy-arn POLICY_ARN \
  --approve
```

Verify:

```bash
kubectl describe sa customer-api-sa -n customer-app
```

Expected:

```text
eks.amazonaws.com/role-arn
```

---

# Step 7 - Application Development

requirements.txt

```text
flask
boto3
gunicorn
```

Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
python app.py
```

Health check:

```bash
curl http://localhost:5000/health
```

Expected:

```text
OK
```

---

# Step 8 - Containerization

## Why?

Docker packages the application and dependencies into a portable image.

Build image:

```bash
docker build -t customer-api:v1 .
```

Verify:

```bash
docker images
```

Run locally:

```bash
docker run -p 5000:5000 customer-api:v1
```

Test:

```bash
curl http://localhost:5000/health
```

---

# Step 9 - Push Image to Amazon ECR

Create repository:

```bash
aws ecr create-repository \
  --repository-name customer-api \
  --region us-east-1
```

Login:

```bash
aws ecr get-login-password \
  --region us-east-1 \
| docker login \
  --username AWS \
  --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

Tag image:

```bash
docker tag customer-api:v1 \
ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/customer-api:v1
```

Push image:

```bash
docker push \
ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/customer-api:v1
```

---

# Step 10 - Deploy Application

deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: customer-api
  namespace: customer-app

spec:
  replicas: 1

  selector:
    matchLabels:
      app: customer-api

  template:
    metadata:
      labels:
        app: customer-api

    spec:
      serviceAccountName: customer-api-sa

      containers:
      - name: customer-api
        image: ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/customer-api:v1
        ports:
        - containerPort: 5000
```

Apply:

```bash
kubectl apply -f k8s/deployment.yaml
```

---

# Create Service

service.yaml

```yaml
apiVersion: v1
kind: Service

metadata:
  name: customer-api
  namespace: customer-app

spec:
  selector:
    app: customer-api

  ports:
  - port: 80
    targetPort: 5000

  type: ClusterIP
```

Apply:

```bash
kubectl apply -f k8s/service.yaml
```

---

# Verification

Check pods:

```bash
kubectl get pods -n customer-app
```

Check logs:

```bash
kubectl logs -n customer-app deployment/customer-api
```

Port forward:

```bash
kubectl port-forward svc/customer-api 5000:80 -n customer-app
```

Health check:

```bash
curl http://localhost:5000/health
```

---

# Customer Operations

Create Customer

```bash
curl -X POST http://localhost:5000/customer \
-H "Content-Type: application/json" \
-d '{
  "customer_id":"101",
  "name":"DK",
  "email":"dk@example.com",
  "city":"Coimbatore"
}'
```

Read Customer

```bash
curl http://localhost:5000/customer/101
```

Update Customer

```bash
curl -X PUT http://localhost:5000/customer/101 \
-H "Content-Type: application/json" \
-d '{
  "name":"DK Updated",
  "email":"dknew@example.com",
  "city":"Chennai"
}'
```

---

# Troubleshooting

## Issue 1 - Python Package Installation Failed

Error:

```text
externally-managed-environment
```

Cause:

Ubuntu 24.04 protects system Python.

Fix:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Issue 2 - Cannot Connect To localhost:5000

Error:

```text
curl: (7) Failed to connect
```

Cause:

Port-forward not running.

Fix:

```bash
kubectl port-forward svc/customer-api 5000:80 -n customer-app
```

---

## Issue 3 - HTTP 500 Internal Server Error

Error:

```text
500 Internal Server Error
```

Cause:

Application crashed while accessing DynamoDB.

Debug:

```bash
kubectl logs -n customer-app deployment/customer-api
```

---

## Issue 4 - AccessDeniedException

Error:

```text
dynamodb:PutItem AccessDenied
```

Cause:

Malformed DynamoDB ARN inside IAM Policy.

Incorrect:

```text
arn:aws:dynamodb:us-east-1:arn:aws:iam::ACCOUNT_ID:table/customers
```

Correct:

```text
arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/customers
```

Fix:

Update IAM Policy and restart deployment.

```bash
kubectl rollout restart deployment customer-api -n customer-app
```

---

## Issue 5 - Validate IRSA

Check environment variables:

```bash
kubectl exec -it deployment/customer-api -n customer-app -- env | grep AWS
```

Expected:

```text
AWS_ROLE_ARN
AWS_WEB_IDENTITY_TOKEN_FILE
```

---

# Security Benefits

Without IRSA:

```text
Pod
 ↓
AWS Access Keys
 ↓
DynamoDB
```

Problems:

* Credential leakage
* Manual rotation
* Long-lived secrets

With IRSA:

```text
Pod
 ↓
Service Account
 ↓
IAM Role
 ↓
STS Temporary Credentials
 ↓
DynamoDB
```

Benefits:

* No AWS keys stored
* Temporary credentials
* Least privilege
* Better security posture

---

# Skills Demonstrated

* Amazon EKS
* Amazon DynamoDB
* Amazon ECR
* IAM Policies
* IAM Roles
* OIDC
* IRSA
* AWS STS
* Kubernetes
* Docker
* Flask
* boto3
* Troubleshooting
* Cloud Security

---

# Cleanup

Delete EKS Cluster:

```bash
eksctl delete cluster \
  --name customer-dynamodb-cluster \
  --region us-east-1
```

Delete DynamoDB Table:

```bash
aws dynamodb delete-table \
  --table-name customers \
  --region us-east-1
```

Delete ECR Repository:

```bash
aws ecr delete-repository \
  --repository-name customer-api \
  --force \
  --region us-east-1
```

---

# Conclusion

This project demonstrates a production-style implementation of secure AWS service access from Kubernetes workloads using IAM Roles for Service Accounts (IRSA). The application successfully performs customer management operations against DynamoDB without using AWS access keys, following cloud-native security best practices and the Principle of Least Privilege.
