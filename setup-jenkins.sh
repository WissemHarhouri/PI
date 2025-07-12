#!/bin/bash

# Jenkins Setup Script
echo "🔧 Setting up Jenkins for ExamGenius project..."

# Check if Jenkins is running
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "❌ Jenkins is not running. Please start it with docker-compose up -d first."
    exit 1
fi

# Get Jenkins initial admin password
echo "🔑 Getting Jenkins initial admin password..."
JENKINS_PASSWORD=$(docker-compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword)

echo ""
echo "📋 Jenkins Setup Instructions:"
echo "1. Open your browser and go to: http://localhost:8080"
echo "2. Use this initial admin password: $JENKINS_PASSWORD"
echo "3. Install suggested plugins"
echo "4. Create an admin user"
echo "5. Configure Jenkins URL (keep default: http://localhost:8080/)"
echo ""
echo "🛠️  Additional Setup Required:"
echo "1. Install Docker Pipeline plugin (if not already installed)"
echo "2. Add Docker Hub credentials (ID: docker-hub-creds)"
echo "3. Create a new Pipeline job for your ExamGenius project"
echo "4. Configure the Pipeline to use your Jenkinsfile from SCM"
echo ""
echo "📂 Project files are available in Jenkins at: /workspace"
echo ""
echo "🔄 To restart Jenkins:"
echo "   docker-compose restart jenkins"
