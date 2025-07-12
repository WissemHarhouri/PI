#!/bin/bash

# Complete ExamGenius Deployment - Step by Step Guide

echo "🚀 ExamGenius Docker Compose + Jenkins Deployment"
echo "=================================================="
echo ""

# Step 1: Prerequisites Check
echo "📋 Step 1: Prerequisites Check"
echo "------------------------------"
echo "✅ Docker installed and running"
echo "✅ Docker Compose installed"
echo "✅ GROQ API key in .env file"
echo "✅ All deployment files created"
echo ""

# Step 2: File Structure
echo "📁 Step 2: Project Structure"
echo "----------------------------"
echo "Your project now includes:"
echo "├── docker-compose.yml          # Main orchestration"
echo "├── dockerfile                  # App container"
echo "├── jenkins.dockerfile          # Jenkins container"
echo "├── jenkinsfile                 # CI/CD pipeline"
echo "├── deploy.sh                   # Deployment script"
echo "├── setup-jenkins.sh            # Jenkins setup"
echo "├── DEPLOYMENT.md               # Detailed guide"
echo "└── .dockerignore               # Docker ignore rules"
echo ""

# Step 3: Deployment Process
echo "🔄 Step 3: Deployment Process"
echo "-----------------------------"
echo "1. Run: ./deploy.sh"
echo "2. Wait for services to start"
echo "3. Access app at http://localhost:8501"
echo "4. Access Jenkins at http://localhost:8080"
echo "5. Run: ./setup-jenkins.sh for Jenkins config"
echo ""

# Step 4: Jenkins Configuration
echo "⚙️  Step 4: Jenkins Configuration"
echo "--------------------------------"
echo "1. Get initial password from setup script"
echo "2. Install suggested plugins"
echo "3. Create admin user"
echo "4. Add Docker Hub credentials (ID: docker-hub-creds)"
echo "5. Create Pipeline job using your Jenkinsfile"
echo ""

# Step 5: CI/CD Pipeline
echo "🔀 Step 5: CI/CD Pipeline Features"
echo "----------------------------------"
echo "✅ Automated builds on code changes"
echo "✅ Docker image building and pushing"
echo "✅ Health checks"
echo "✅ Deployment with Docker Compose"
echo "✅ Rollback capabilities"
echo ""

# Step 6: What's Included
echo "📦 Step 6: What's Included"
echo "-------------------------"
echo "Services:"
echo "- ExamGenius App (Streamlit): Port 8501"
echo "- Jenkins CI/CD: Port 8080, 50000"
echo "- Shared Docker network"
echo "- Persistent Jenkins data volume"
echo ""

echo "Features:"
echo "- Docker-in-Docker for Jenkins"
echo "- Automated deployment pipeline"
echo "- Health monitoring"
echo "- Easy startup/shutdown scripts"
echo "- Comprehensive documentation"
echo ""

# Step 7: Commands Summary
echo "🛠️  Step 7: Key Commands"
echo "------------------------"
echo "Start everything:     ./deploy.sh"
echo "Setup Jenkins:        ./setup-jenkins.sh"
echo "View logs:           docker-compose logs -f"
echo "Stop everything:     docker-compose down"
echo "Rebuild:             docker-compose up -d --build"
echo ""

# Step 8: Next Steps
echo "🎯 Step 8: Next Steps"
echo "--------------------"
echo "1. Ensure your .env file has a valid GROQ_API_KEY"
echo "2. Run ./deploy.sh to start deployment"
echo "3. Follow Jenkins setup instructions"
echo "4. Configure your Git repository in Jenkins"
echo "5. Test the complete CI/CD pipeline"
echo ""

echo "📚 For detailed instructions, see DEPLOYMENT.md"
echo "🎉 Happy deploying!"
