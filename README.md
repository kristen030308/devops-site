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
> docker run --name devops-site -p 5000:5000 devops:latest

5. Push the image to the dockerHub

Run: 
> docker login

Run:
> docker tag devops:v1 <docker-hub-username>/devops:latest

Run:
> docker push <docker-hub-username>/devops:latest

6. jenkinsfile

Go to jenkins manage and select the configuration, add the docker cradentials. **Note: Id = DOCKERHUB_CRAD "

create a pipeline and paste the content.

pipeline {
  agent any

  triggers {
    githubPush()
  }

  environment {
    IMAGE = "devops-site:"
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
      echo "Build ${env.VERSION} deployed successfully."
    }
    failure {
      echo "Pipeline failed. Check the logs above."
    }
    always {
      sh "docker logout || true"
    }
  }
}