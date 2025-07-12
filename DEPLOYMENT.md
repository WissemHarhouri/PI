# ExamGenius Deployment Guide

This guide will help you deploy the ExamGenius application using Docker Compose with Jenkins CI/CD.

## Prerequisites

- Docker installed and running
- Docker Compose installed
- Git (for Jenkins SCM integration)
- A valid GROQ API key

## Quick Start

### 1. Environment Setup

1. Make sure your `.env` file contains your GROQ API key:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

2. Make the deployment script executable:
   ```bash
   chmod +x deploy.sh setup-jenkins.sh
   ```

### 2. Deploy the Application

Run the deployment script:
```bash
./deploy.sh
```

This will:
- Check prerequisites
- Build and start all services
- Display access information

### 3. Access the Application

- **ExamGenius App**: http://localhost:8501
- **Jenkins**: http://localhost:8080

### 4. Configure Jenkins

1. Run the Jenkins setup script:
   ```bash
   ./setup-jenkins.sh
   ```

2. Follow the displayed instructions to complete Jenkins setup

## Services Overview

### ExamGenius Application
- **Port**: 8501
- **Description**: Main Streamlit application
- **Dependencies**: Jenkins (for CI/CD)

### Jenkins
- **Port**: 8080 (Web UI), 50000 (Agent communication)
- **Description**: CI/CD server with Docker support
- **Features**:
  - Docker CLI and Docker Compose installed
  - Blue Ocean plugin for better UI
  - Docker workflow plugins
  - Access to host Docker daemon

## Manual Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Rebuild Services
```bash
docker-compose up -d --build
```

### Jenkins Initial Password
```bash
docker-compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

## Jenkins Pipeline Configuration

### 1. Create a New Pipeline Job

1. Go to Jenkins dashboard
2. Click "New Item"
3. Enter job name (e.g., "ExamGenius-Pipeline")
4. Select "Pipeline"
5. Click "OK"

### 2. Configure Pipeline

In the job configuration:

1. **General**: Add description
2. **Build Triggers**: Configure as needed (e.g., GitHub webhook)
3. **Pipeline**: 
   - Definition: "Pipeline script from SCM"
   - SCM: Git
   - Repository URL: Your Git repository URL
   - Script Path: `jenkinsfile`

### 3. Required Credentials

Add these credentials in Jenkins:
- **docker-hub-creds**: Docker Hub username and password/token

## Troubleshooting

### Common Issues

1. **Docker daemon not accessible in Jenkins**
   - Ensure Docker socket is mounted correctly
   - Check Jenkins has proper permissions

2. **Port conflicts**
   - Ensure ports 8080 and 8501 are not in use
   - Modify docker-compose.yml if needed

3. **GROQ API key issues**
   - Verify the key is correctly set in .env
   - Check the key has proper permissions

### Debug Commands

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs jenkins
docker-compose logs examgenius-app

# Enter Jenkins container
docker-compose exec jenkins bash

# Enter app container
docker-compose exec examgenius-app bash
```

## File Structure

```
.
├── docker-compose.yml          # Main orchestration file
├── dockerfile                  # Application Dockerfile
├── jenkins.dockerfile          # Custom Jenkins Dockerfile
├── jenkinsfile                 # CI/CD pipeline definition
├── deploy.sh                   # Deployment script
├── setup-jenkins.sh            # Jenkins setup script
├── .env                        # Environment variables
└── src/                        # Application source code
```

## Security Considerations

1. **Jenkins Security**:
   - Change default admin password
   - Enable proper authentication
   - Use role-based access control

2. **Docker Security**:
   - Run containers with minimal privileges where possible
   - Regularly update base images
   - Use multi-stage builds for production

3. **API Keys**:
   - Never commit API keys to version control
   - Use environment variables or secret management
   - Rotate keys regularly

## Production Deployment

For production deployment, consider:

1. **Use external volumes for persistence**
2. **Implement proper backup strategy**
3. **Use reverse proxy (nginx/traefik)**
4. **Enable HTTPS/SSL**
5. **Set up monitoring and logging**
6. **Use orchestration platforms (Kubernetes, Docker Swarm)**

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Docker Compose logs
3. Consult Jenkins documentation
4. Check application-specific logs
