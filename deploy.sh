#!/bin/bash

# ExamGenius Deployment Script
echo "🚀 Starting ExamGenius deployment with Docker Compose and Jenkins..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it first."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env file..."
    export $(cat .env | xargs)
else
    echo "⚠️  .env file not found. Please create one with your GROQ_API_KEY."
    exit 1
fi

# Check if GROQ_API_KEY is set
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ GROQ_API_KEY is not set in .env file."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check service status
echo "📋 Checking service status..."
docker-compose ps

# Display access information
echo ""
echo "✅ Deployment complete!"
echo "🌐 Access your application at: http://localhost:8501"
echo "🔧 Access Jenkins at: http://localhost:8080"
echo ""
echo "📝 To get Jenkins initial admin password, run:"
echo "   docker-compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
echo ""
echo "🔄 To stop all services:"
echo "   docker-compose down"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f"
