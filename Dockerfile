# =============================================================================
# Educational Python HTTP Server Dockerfile
# =============================================================================
# 
# This Dockerfile demonstrates containerization concepts for the Python-based
# HTTP server migration project. It supports both native Python http.server
# and Flask framework implementations for comprehensive learning.
# 
# Key Educational Concepts Demonstrated:
# - Multi-stage Docker builds for optimization
# - Python runtime environment configuration
# - Dependency management in containerized applications
# - Port exposure and networking configuration
# - Best practices for Python containerization
# =============================================================================

# =============================================================================
# Stage 1: Base Python Runtime Environment
# =============================================================================
# Using Python 3.8 Alpine Linux for minimal footprint and security
# Alpine Linux provides a lightweight container base (~5MB vs ~900MB for full Python)
FROM python:3.8-alpine AS base

# Set environment variables for Python optimization in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Add metadata labels for container identification and documentation
LABEL maintainer="Blitzy Platform Educational Team" \
      version="1.0.0" \
      description="Educational Python HTTP Server with native and Flask implementations" \
      python.version="3.8+" \
      framework.native="http.server" \
      framework.web="Flask 2.3.2"

# =============================================================================
# Stage 2: Development Dependencies (Optional Enhancement)
# =============================================================================
# This stage installs build dependencies that may be needed for some Python packages
# Most educational projects won't need this, but it's included for completeness
FROM base AS dependencies

# Install system dependencies for potential Python package compilation
# These are commonly needed for Python packages with C extensions
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# =============================================================================
# Stage 3: Application Environment Setup
# =============================================================================
FROM base AS application

# Create application directory with appropriate permissions
# Using /app as conventional Docker application directory
WORKDIR /app

# Create non-root user for security best practices
# Running applications as non-root reduces security risks
RUN addgroup -g 1000 appgroup && \
    adduser -D -s /bin/sh -u 1000 -G appgroup appuser

# =============================================================================
# Stage 4: Dependency Installation and Application Code
# =============================================================================

# Copy requirements.txt first for Docker layer caching optimization
# This allows Docker to cache the pip install layer if dependencies don't change
COPY requirements.txt* ./

# Install Python dependencies conditionally
# The requirements.txt file is only needed for Flask implementation
# Native Python implementation requires no external dependencies
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "No requirements.txt found - using native Python only"; \
    fi

# Copy application source code
# Copying after dependency installation optimizes Docker build caching
COPY . .

# Set appropriate file permissions
# Ensure the appuser can read all application files
RUN chown -R appuser:appgroup /app

# Switch to non-root user for security
USER appuser

# =============================================================================
# Network Configuration
# =============================================================================

# Expose port 3000 as the default HTTP server port
# This is configurable via environment variables at runtime
EXPOSE 3000

# Additional commonly used ports for educational flexibility
# Uncomment these if you want to expose multiple ports
# EXPOSE 8000
# EXPOSE 8080

# =============================================================================
# Runtime Configuration
# =============================================================================

# Set environment variables with sensible defaults
# These can be overridden at container runtime for different configurations
ENV PORT=3000 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app

# =============================================================================
# Application Execution Options
# =============================================================================

# Default command runs the Flask implementation
# This provides the most feature-complete experience for beginners
CMD ["python", "app.py"]

# =============================================================================
# Alternative Execution Commands (Educational Examples)
# =============================================================================
# 
# The following examples show different ways to run the containerized application:
# 
# 1. Run Flask implementation (default):
#    docker run -p 3000:3000 python-server
# 
# 2. Run native Python implementation:
#    docker run -p 3000:3000 python-server python server.py
# 
# 3. Run with custom port:
#    docker run -p 8080:8080 -e PORT=8080 python-server
# 
# 4. Run Flask with development server:
#    docker run -p 3000:3000 -e FLASK_ENV=development python-server flask run --host=0.0.0.0
# 
# 5. Run with environment variables:
#    docker run -p 3000:3000 -e DEBUG=True -e HOST=0.0.0.0 python-server
# 
# =============================================================================

# =============================================================================
# Health Check Configuration
# =============================================================================

# Health check to verify the HTTP server is responding correctly
# This enables container orchestration systems to monitor application health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/hello')" || exit 1

# =============================================================================
# Volume Configuration (Optional)
# =============================================================================

# Optional volume mount point for development
# Uncomment this if you want to enable live code reloading during development
# VOLUME ["/app"]

# =============================================================================
# Build Arguments for Customization
# =============================================================================

# Build arguments allow customization at build time
# Example: docker build --build-arg PYTHON_VERSION=3.9 .
ARG PYTHON_VERSION=3.8
ARG APP_VERSION=1.0.0

# =============================================================================
# Documentation and Usage Instructions
# =============================================================================
# 
# BUILD INSTRUCTIONS:
# ===================
# 
# 1. Build the Docker image:
#    docker build -t python-http-server .
# 
# 2. Build with custom Python version:
#    docker build --build-arg PYTHON_VERSION=3.9 -t python-http-server .
# 
# 3. Build for specific platform:
#    docker build --platform linux/amd64 -t python-http-server .
# 
# RUN INSTRUCTIONS:
# =================
# 
# 1. Run Flask implementation (recommended for beginners):
#    docker run -d -p 3000:3000 --name http-server python-http-server
# 
# 2. Run native Python implementation:
#    docker run -d -p 3000:3000 --name http-server python-http-server python server.py
# 
# 3. Run with custom configuration:
#    docker run -d -p 8080:8080 -e PORT=8080 --name http-server python-http-server
# 
# 4. Run in interactive mode for debugging:
#    docker run -it -p 3000:3000 python-http-server /bin/sh
# 
# TESTING INSTRUCTIONS:
# ====================
# 
# 1. Test the /hello endpoint:
#    curl http://localhost:3000/hello
# 
# 2. Expected response:
#    Hello world
# 
# 3. Check container health:
#    docker ps (should show "healthy" status)
# 
# 4. View container logs:
#    docker logs http-server
# 
# DEVELOPMENT WORKFLOW:
# ====================
# 
# 1. For development with live reloading:
#    docker run -it -p 3000:3000 -v $(pwd):/app python-http-server
# 
# 2. For debugging:
#    docker run -it -p 3000:3000 python-http-server /bin/sh
# 
# 3. For production-like testing:
#    docker run -d -p 3000:3000 --restart unless-stopped python-http-server
# 
# =============================================================================