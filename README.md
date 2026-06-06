# Phase 1

1. Git clone the application
> git clone https://github.com/Devopsplan/devops-site-end-to-end.git


2. Install the requirements.txt

Run:
> pip install -r requirements.txt

Run the application:
> python app.py

3. Create a Dockerfile with the mention content

# Use official Python slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app.py .
COPY data/ data/
COPY static/ static/
COPY templates/ templates/

# Expose Flask port
EXPOSE 5000

# Run with gunicorn in production
CMD ["python", "app.py"]

4. Docker Image and container 

Run:
> docker build -t devops .

Run:
> docker run -it --name devops-site -p 5000:5000 devops:latest

5. Push the image to the dockerHub

Run: 
> docker login

Run:
> docker tag devops:latest <docker-hub-username>/devops:latest

Run:
> docker push <docker-hub-username>/devops:latest

6. jenkinsfile

Go to manage-jenkins and select the Credentials, add the docker cradentials. **Note: Id = DOCKERHUB_CRAD "

create a pipeline and paste the content.

pipeline {
  agent any

  environment {
    IMAGE = "devops-site"
    DOCKER_USER = "<docker-username>"
  }

  stages {

    stage('Checkout') {
      steps {
        git branch: 'main',
            url: 'https://github.com/Devopsplan/devops-site-end-to-end.git'
      }
    }

    stage('Build') {
      steps {
        script {
          def VERSION = sh(script: "date +%Y%m%d%H%M", returnStdout: true).trim()
          env.VERSION = VERSION
        }
        sh "docker build -t ${IMAGE}:${env.VERSION} ."
      }
    }

    stage('Login & Push') {
      steps {
        withCredentials([usernamePassword(
              credentialsId: 'DOCKERHUB_CRAD',
          usernameVariable: 'DOCKER_USER',
          passwordVariable: 'DOCKER_PASS'
        )]) {
          sh """
            echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin
            docker tag ${IMAGE}:${env.VERSION} \$DOCKER_USER/${IMAGE}:${env.VERSION}
            docker push \$DOCKER_USER/${IMAGE}:${env.VERSION}
          """
        }
      }
    }

    stage('Deploy') {
      steps {
        sh """
          docker stop ${IMAGE} || true
          docker rm   ${IMAGE} || true
          docker run -d \
            --name ${IMAGE} \
            --restart unless-stopped \
            -p 5000:5000 \
            \$DOCKER_USER/${IMAGE}:${env.VERSION}
        """
      }
    }

  }

  post {
    success {
      echo "Build ${env.VERSION} deployed successfully and Jenkins done."
    }
    failure {
      echo "Pipeline failed. Check the logs above."
    }
    always {
      sh "docker logout || true"
    }
  }
}



8. Now we are creating a kubernetes cluster with terraform
--------------------------------------------

* First we need to configure aws credentials with terraform or terimal 

Need to download: 
- [ ] AWS Cli
- [ ] Terraform
- [ ] Kubectl
- [ ] Helm
- [ ] EKSCTL


Download:

If you have Windows Subsystem for Linux (WSL) installed, you can use Linux commands to install eksctl, kubectl, and AWS CLI on your WSL environment. Here's how:

1. Install eksctl on WSL
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```
2. Install kubectl on WSL
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

3. Install AWS CLI on WSL
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify installations
```bash
eksctl version
kubectl version --client
aws --version
```



A. Create a IAM role with the policy 

Managed Policy                           Purpose
AmazonEKSClusterPolicy                   EKS cluster operations
AmazonEKSWorkerNodePolicyNode            group permissions
AmazonEKS_CNI_Policy                     VPC CNI add-on
AmazonEC2ContainerRegistryReadOnly       Pull images from ECR 
AmazonVPCFullAccess                      VPC/subnet/NAT/IGW
IAMFullAccessRole                        creation for EKS (scope down in prod)


A. Configure aws credentials 

    > aws configure 

B. Create a terraform file for kubernetes cluster

----------------------------------------------------------------
terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# VPC module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name            = "my-vpc"
  cidr            = "10.0.0.0/16"
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# EKS Cluster module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = "my-cluster"        # was: cluster_name
  kubernetes_version = "1.30"              # was: cluster_version

  addons = {                               # was: cluster_addons
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    vpc-cni                = { most_recent = true }
    eks-pod-identity-agent = { most_recent = true }
  }

  endpoint_public_access                   = true   # was: cluster_endpoint_public_access
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.micro"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}
  
------------------------------------------------------------------

> terraform init
> terraform plan
> terraform apply
> rm -rf .terraform .terraform.lock.hcl     # delete the terraform lock files and then
  > terraform init
  > terraform plan

> terraform apply -auto-approve 

Once apply finishes, connect to your cluster:

** Note = if you create a any loadbalance please change into cluster ip and then apply the terraform destroy Why because terraform try to destroy but not successful in deleting lb because some dependecy on lb and it convert into infinite loop **

# Create access entry
aws eks list-access-entries \
  --cluster-name my-cluster \
  --region us-east-1

# Attach admin policy
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::701201543425:user/New-eks \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy \
  --access-scope type=cluster \
  --region us-east-1

> kubectl get nodes



![alt text](image-1.png)

9. Now we are creating a kubernetes deployment and service
--------------------------------------------
Create the deployment.yaml file
---------------------------------
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devops-site-deployment
  namespace: default   # if you create a namespace please use that namespace here
  labels:
    app: devops-site    # this lable is very important please use this label in service yaml file
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devops-site
  template:
    metadata:
      labels:
        app: devops-site
    spec:
      containers:
      - name: devops-site-flask-app
        image: devoopsguru/hello:2026-05-15-132410
        ports:
        - containerPort: 5000


---

## create the service yaml file

apiVersion: v1
kind: Service
metadata:
  name: devops-site-service
  namespace: default   # if you create a namespace please use that namespace here
  labels:
    app: devops-site    # this lable is very important please use this label in service yaml file 
    release: prometheus
spec:
  selector:
    app: devops-site
  ports:
  - name: http
    protocol: TCP
    port: 80
    targetPort: 5000
  type: ClusterIP

--------------------------------------------------------

> kubectl apply -f deployment.yaml


> kubectl get all -n default or kubectl get all

![alt text](image-2.png)

> kubectl port-forward service/devops-site-service 8080:80


10. Monitoring tools ( prometheus and grafana)
----------------------------------------

we are installing the prometheus via the helm :

> helm version

# Step 1 - Install Helm
sudo snap install helm --classic

# Step 2 - Verify
helm version

# Step 3 - Add Prometheus repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Step 4 - Update repos
helm repo update

# Step 5 - Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

# Step 6 - Check everything in monitoring namespace
kubectl get all -n monitoring


Now modify the requirement.txt file

Replace the content :

Flask==2.3.3
prometheus-client==0.21.0
prometheus-flask-exporter==0.23.1
gunicorn==22.0.0

Now modify the app.py file ( Replace the content ) 

whole file like :

--------------------------------------------
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from prometheus_flask_exporter import PrometheusMetrics
import json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
app.config["SECRET_KEY"] = "replace-with-a-secure-secret"

metrics = PrometheusMetrics.for_app_factory()
metrics.init_app(app)
metrics.info("app_info", "DevOps Academy App", version="1.0.0")


def load_json(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return json.load(file)


courses = load_json("courses.json")
roadmap = load_json("roadmap.json")
testimonials = load_json("testimonials.json")

contact = {
    "phone": "+91 97982-53860",
    "email": "info@devopsacademy.co",
    "address": "BTM Layout, Bengaluru, Karnataka 560076",
    "website": "www.devopsacademy.co",
}


@app.route("/")
def home():
    return render_template(
        "index.html",
        courses=courses,
        roadmap=roadmap,
        testimonials=testimonials,
        contact=contact,
    )


@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email:
        flash("Name and email are required. Please complete the form.", "error")
        return redirect(url_for("home") + "#enroll")

    flash("Thank you! Your enrollment request has been received.", "success")
    app.logger.info("Enrollment request: %s, %s, %s, %s", name, email, phone, message)
    return redirect(url_for("home") + "#enroll")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
-----------------------------------------------------------
Next Steps

add or change the docker-file:

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY data/ data/
COPY static/ static/
COPY templates/ templates/

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]

---------------------------------------------------------------------
After updating these files, rebuild and push your Docker image:

docker build -t devoopsguru/hello:<new-tag> .
docker push devoopsguru/hello:<new-tag>

# Step 1 - Update deployment with new image via terminal	
kubectl set image deployment/devops-site-deployment devops-site-flask-app=devopsplan1999/devops-site:v3

# Step 2 - Watch rollout
kubectl rollout status deployment/devops-site-deployment

# Step 3 - Verify pods are running
kubectl get pods

Then test the /metrics endpoint:

# Step 4 - Port forward
kubectl port-forward svc/devops-site-service 8080:80

# Step 5 - In a NEW terminal, test metrics
curl http://localhost:8080/metrics

http://[IP_ADDRESS]/metrics --> prometheus 

11. define the prometheus configmap 

here we have a two option 
A. via edit prometheus.yaml file 
B. via servicemonitor.yaml file

we are using option B because it is the best practice.

create the servicemonitor.yaml file
-------------------------------------------------

apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: devops-site-servicemonitor
  namespace: monitoring
  labels:
    release: prometheus        # must match your Prometheus operator label selector
spec:
  selector:
    matchLabels:
      app: devops-site         # must match your service label
      release: prometheus      # must match your service label
  namespaceSelector:
    matchNames:
      - default
  endpoints:
  - port: http                 # must match port name in service.yaml
    path: /metrics
    interval: 15s

-------------------------------------------------

> kubectl apply -f servicemonitor.yaml
> kubectl get all -n monitoring

> kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
>
> Now go to url and click on status >> target health

> enter the quarry : {job="devops-site-service"} and execute. 
> Also try : app_info

Grafana Dashboard
----------------------------------------
 
> grafana password:
kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

Ui is working on 9093 now we can port mapping
> kubectl port-forward -n monitoring svc/prometheus-grafana 9093:80


Dashboard setup:

Click in DashBoard and Right side + icon . click on that and select Import dashboard.

> In the find filed enter the code of "3662"
>  grafana dashboard templates can search on googles as per the requirement you can set the dashboard.


Continous delivery ( ArgoCD )
----------------------------------------------------------------------------------------

1. Automate the CI
------------------------------
add the stage in the jenkinsfile

stage('Update Deployment File') {
    steps {
        sh """
        sed -i 's|image: .*|image: ${DOCKERHUB_USERNAME}/flask-hello:${IMAGE_TAG}|' deployment.yaml

        git config user.name "Jenkins"
        git config user.email "jenkins@example.com"

        git add deployment.yaml
        git commit -m "Deploy new image ${IMAGE_TAG}"
        git push
        """
    }
}

whole pipeline

pipeline {
    agent any

    environment {
        IMAGE_NAME = "devoopsguru/hello"
        DEPLOYMENT_FILE = "deployment.yaml"
    }

    stages {

        stage('Git Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Generate Image Tag') {
            steps {
                script {
                    env.IMAGE_TAG = new Date().format("yyyy-MM-dd-HHmmss")
                    env.FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"

                    echo "Image Name: ${FULL_IMAGE}"
                }
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'docker_cred',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {

                    sh '''
                    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                docker build -t ${FULL_IMAGE} .
                '''
            }
        }

        stage('Push Docker Image') {
            steps {
                sh '''
                docker push ${FULL_IMAGE}
                '''
            }
        }

        stage('Update Kubernetes Deployment File') {
            steps {
                sh """
                sed -i 's|image: .*|image: ${FULL_IMAGE}|' ${DEPLOYMENT_FILE}

                git config user.name "Jenkins"
                git config user.email "jenkins@example.com"

                git add ${DEPLOYMENT_FILE}
                git commit -m "Updated image to ${FULL_IMAGE}" || echo "No changes to commit"

                git push
                """
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                kubectl apply -f deployment.yaml
                '''
            }
        }

    }

    post {

        success {
            echo "Pipeline executed successfully"
        }

        failure {
            echo "Pipeline failed"
        }

    }
}

2. Install the ArgoCD

kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

> kubeclt get all -n argocd

kubectl patch svc argocd-server -n argocd -p "{\"spec\": {\"type\": \"LoadBalancer\"}}"

** Note: Port forward works BUT for ArgoCD in Codespace doesn't run...
Don't know why....
** 

kubeclt get svc -n agrocd

copy the external IP of argocd-server and open it with new tab
Username: admin
Password: 
kubectl get secret argocd-secret -n argocd -o jsonpath="{.data.server\.secretkey}" | base64 -d

after the login 

- click on application and set-up that.
  General:
  Appication Name: demo or any
  Project Name: Default
  Sync Policy: Automati and check-mark down box.

  Source:
  Repo link:
  Revision: main
  Path: .
  Destination:
  Cluster URL : default on chooose
  NameSpace: default

  Scroll up and click on edit as yaml

  apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<username>/hello.git
    targetRevision: main
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true

  Save and exit


  Now check the replicas and enjoy the full projet automate.
  
