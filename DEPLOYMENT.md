# OI Sandbox - Portable Open Interpreter

A fully sandboxed, portable Open Interpreter setup that can run on any system with Docker.

## 🚀 Quick Start

### Prerequisites
- Docker installed on target system
- OpenAI API key (set as environment variable)

### Local Setup
```bash
# Make scripts executable
chmod +x build.sh run.sh

# Build and run
./run.sh
```

Access at: http://localhost:8501

## 📦 Deployment Options

### 1. USB Drive Deployment

Perfect for portable, offline use on any system with Docker.

#### Step 1: Build the Package
```bash
./build.sh
```

#### Step 2: Create USB Package
```bash
# Save Docker image as portable file
docker save oi-sandbox:latest > oi-sandbox.tar

# Copy files to USB drive
cp oi-sandbox.tar docker-compose.yml run.sh workspace/ /path/to/usb/
```

#### Step 3: Deploy on Target System
```bash
# Insert USB drive
cd /path/to/usb

# Load Docker image
docker load < oi-sandbox.tar

# Set your API key
export OPENAI_API_KEY="your-api-key-here"

# Run the app
docker-compose up -d

# Access at http://localhost:8501
```

### 2. Google Drive Deployment

Share with others or store in the cloud.

#### Option A: Docker Registry (Recommended)
```bash
# Login to Docker Hub (or your registry)
docker login

# Tag and push
docker tag oi-sandbox:latest yourusername/oi-sandbox:latest
docker push yourusername/oi-sandbox:latest

# Share this command with others:
# docker run -p 8501:8501 -e OPENAI_API_KEY=your-key yourusername/oi-sandbox:latest
```

#### Option B: Direct File Sharing
```bash
# Create complete package
tar -czf oi-sandbox-complete.tar.gz ./

# Upload oi-sandbox-complete.tar.gz to Google Drive
# Share the download link

# Others can extract and run:
# tar -xzf oi-sandbox-complete.tar.gz
# cd oi-sandbox
# ./run.sh
```

### 3. Google Cloud Platform Deployment

#### Using Google Cloud Run
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/your-project/oi-sandbox

# Deploy to Cloud Run
gcloud run deploy oi-sandbox \
  --image gcr.io/your-project/oi-sandbox \
  --platform managed \
  --port 8501 \
  --set-env-vars OPENAI_API_KEY=your-key
```

#### Using Google Compute Engine
```bash
# Create VM instance
gcloud compute instances create oi-instance \
  --machine-type e2-medium \
  --image-family ubuntu-2004-lts \
  --image-project ubuntu-os-cloud

# SSH and install Docker
gcloud compute ssh oi-instance
# Install Docker and run the app
```

## 🔧 Configuration

### Environment Variables
Set these before running:

```bash
export OPENAI_API_KEY="your-openai-key"
export OPENROUTER_API_KEY="your-openrouter-key"  # Optional
export API_BASE="custom-api-endpoint"           # Optional
export AZURE_ENDPOINT="azure-endpoint"          # Optional
export API_VERSION="api-version"                # Optional
```

### Volume Mounts
The setup automatically mounts:
- `./workspace` - For file storage
- `./chats.db` - For conversation persistence

## 🛡️ Security Features

- **Sandbox Execution**: Code runs in isolated containers
- **Resource Limits**: CPU and memory restrictions
- **No New Privileges**: Restricted system access
- **Read-Only Filesystem**: Prevents system modifications

## 🐳 Docker Image Details

- **Base Image**: Python 3.11 slim
- **Size**: ~500MB (optimized)
- **Ports**: 8501 (Streamlit UI)
- **User**: Non-root for security

## 📋 System Requirements

- **Docker**: Version 20.10+
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 1GB free space
- **OS**: Linux, macOS, Windows (with Docker Desktop)

## 🔄 Updates

To update the sandbox:
```bash
# Pull latest changes
git pull

# Rebuild
./build.sh

# Restart
docker-compose down && docker-compose up -d
```

## 🆘 Troubleshooting

**App won't start:**
```bash
# Check logs
docker-compose logs

# Check if port 8501 is available
netstat -tlnp | grep 8501
```

**Permission issues:**
```bash
# On Linux, add user to docker group
sudo usermod -aG docker $USER
```

**API key not working:**
- Ensure OPENAI_API_KEY is set before running
- Check API key validity
- Verify internet connection

### 4. Work Computer Deployment (No Admin Rights)

Perfect for corporate environments where Docker installation is restricted.

#### Portable Python Setup (No Installation Required)
```bash
# Run the portable setup script
chmod +x setup_portable.sh
./setup_portable.sh
```

This creates a self-contained `oi-portable/` directory with:
- Virtual environment (no admin rights needed)
- All dependencies installed
- Portable across systems

#### Run on Work Computer
```bash
# Navigate to portable directory
cd oi-portable

# Set API key (optional, can be set in UI)
export OPENAI_API_KEY="your-key-here"

# Run the app
./run.sh
```

#### Sandboxing on Work Computers
OI automatically uses the best available sandbox:
1. 🐳 **Docker** (if available)
2. 🔥 **Firejail** (if available on Linux)
3. 🐍 **Python Sandbox** (restricted execution environment)
4. 💻 **Local** (fallback)

The Python sandbox provides basic isolation without Docker:
- Restricted built-in functions
- No access to dangerous modules
- Captured output only

#### Work Computer Features
- ✅ **No Admin Rights Required**
- ✅ **Portable Directory Structure**
- ✅ **Isolated Virtual Environment**
- ✅ **Automatic Sandbox Fallback**
- ✅ **No System Installation**

#### File Access
Files created by OI are stored in `./workspace/` within the portable directory.

#### USB + Work Computer Combo
1. Prepare on personal computer: `./setup_portable.sh`
2. Copy `oi-portable/` to USB drive
3. On work computer: Run `./oi-portable/run.sh`

This gives you a fully functional OI environment on any work computer! 🏢
