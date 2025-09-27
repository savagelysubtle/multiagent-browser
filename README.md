<img src="./assets/web-ui.png" alt="Multiagent Browser" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/savagelysubtle/multiagent-browser?style=social)](https://github.com/savagelysubtle/multiagent-browser/stargazers)
[![License](https://img.shields.io/github/license/savagelysubtle/multiagent-browser)](https://github.com/savagelysubtle/multiagent-browser/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Enhanced-green)](https://www.trychroma.com/)

# Multiagent Browser with Enhanced Document Intelligence

This project is an enhanced fork of the [browser-use](https://github.com/browser-use/browser-use) project, designed to make websites accessible for AI agents with advanced document management capabilities.

We acknowledge the original [browser-use](https://github.com/browser-use/web-ui) project and [WarmShao](https://github.com/warmshao) for their foundational contributions.

## 🚀 **Key Enhancements**

**📊 ChromaDB Integration:** Advanced vector database for intelligent document storage, chunking, and semantic search capabilities.

**📝 Smart Document Pipeline:** Automatic document processing, relationship mapping, and policy compliance checking.

**🔍 Enhanced Search:** Hybrid search combining vector similarity with metadata filtering for precise document retrieval.

**🤖 Agent-Ready Architecture:** Built-in document context injection for AI agents with policy and template suggestions.

**💾 Persistent Knowledge Base:** Multi-collection document storage with versioning, relations, and comprehensive analytics.

## 🔧 **Core Features**

**Multiagent Interface:** Built on Gradio with intuitive controls for multiple AI agent interactions.

**Expanded LLM Support:** Google, OpenAI, Azure OpenAI, Anthropic, DeepSeek, Ollama, and more.

**Custom Browser Support:** Use your own browser with persistent sessions and high-definition recording.

**Document Editor:** Integrated editor with database auto-storage, search, and intelligent suggestions.

## 🎯 **What Makes This Different**

This enhanced version transforms the original browser-use project into a comprehensive document intelligence platform:

- **🧠 Smart Knowledge Base:** Every document you create is automatically stored, chunked, and indexed for intelligent retrieval
- **🔗 Relationship Mapping:** Documents are automatically linked to related policies, templates, and procedures
- **🤖 AI Agent Enhancement:** Agents now have access to your entire document corpus for context-aware responses
- **📋 Policy Compliance:** Real-time checking against your organization's policies and guidelines
- **💡 Intelligent Suggestions:** Get template and content suggestions based on what you're writing
- **🔍 Hybrid Search:** Find documents through semantic meaning or specific metadata filters

<video src="https://github.com/user-attachments/assets/56bc7080-f2e3-4367-af22-6bf2245ff6cb" controls="controls">Your browser does not support playing this video!</video>

## 📦 Installation Guide

### Option 1: Local Installation

Read the [quickstart guide](https://docs.browser-use.com/quickstart#prepare-the-environment) or follow the steps below to get started.

#### Step 1: Clone the Repository
```bash
https://github.com/savagelysubtle/multiagent-browser.git
cd multiagent-browser
```

#### Step 2: Set Up Python Environment
We recommend using [uv](https://docs.astral.sh/uv/) for managing the Python environment.

Using uv (recommended):
```bash
uv venv --python 3.13
```

Activate the virtual environment:
- Windows (Command Prompt):
```cmd
.venv\Scripts\activate
```
- Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```
- macOS/Linux:
```bash
source .venv/bin/activate
```

#### Step 3: Install Dependencies
Install Python packages:
```bash
uv sync
uv sync --all-groups # this will add dev dependencies like ruff
```

Install Browsers in playwright.
```bash
playwright install --with-deps
```
Or you can install specific browsers by running:
```bash
playwright install chromium --with-deps
```

#### Step 4: Configure Environment
1. Create a copy of the example environment file:
- Windows (Command Prompt):
```bash
copy .env.example .env
```
- macOS/Linux/Windows (PowerShell):
```bash
cp .env.example .env
```
2. Open `.env` in your preferred text editor and add your API keys and other settings

#### Step 5: Enjoy the web-ui
1.  **Run the WebUI:**
```bash
python webui.py --ip 127.0.0.1 --port 7788
```
2. **Access the WebUI:** Open your web browser and navigate to `http://127.0.0.1:7788`.
3. **Using Your Own Browser(Optional):**
  - Set `BROWSER_PATH` to the executable path of your browser and `BROWSER_USER_DATA` to the user data directory of your browser. Leave `BROWSER_USER_DATA` empty if you want to use local user data.
    - Windows
```env
 BROWSER_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
 BROWSER_USER_DATA="C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
```
> Note: Replace `YourUsername` with your actual Windows username for Windows systems.
- Mac
```env
 BROWSER_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
 BROWSER_USER_DATA="/Users/YourUsername/Library/Application Support/Google/Chrome"
```
- Close all Chrome windows
- Open the WebUI in a non-Chrome browser, such as Firefox or Edge. This is important because the persistent browser context will use the Chrome data when running the agent.
- Check the "Use Own Browser" option within the Browser Settings.

### Option 2: Docker Installation

#### Prerequisites
- Docker and Docker Compose installed
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) (For Windows/macOS)
  - [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) (For Linux)

#### Step 1: Clone the Repository
```bash
git clone https://github.com/savagelysubtle/multiagent-browser.git
cd multiagent-browser
```

#### Step 2: Configure Environment
1. Create a copy of the example environment file:
- Windows (Command Prompt):
```bash
copy .env.example .env
```
- macOS/Linux/Windows (PowerShell):
```bash
cp .env.example .env
```
2. Open `.env` in your preferred text editor and add your API keys and other settings

#### Step 3: Docker Build and Run
```bash
docker compose up --build
```
For ARM64 systems (e.g., Apple Silicon Macs), please run follow command:
```bash
TARGETPLATFORM=linux/arm64 docker compose up --build
```

#### Step 4: Enjoy the web-ui and vnc
- Web-UI: Open `http://localhost:7788` in your browser
- VNC Viewer (for watching browser interactions): Open `http://localhost:6080/vnc.html`
  - Default VNC password: "youvncpassword"
  - Can be changed by setting `VNC_PASSWORD` in your `.env` file

## 📈 Changelog

### Enhanced Version (Multiagent-Browser)
- [x] **2025/09/27:** 🚀 **Major Enhancement:** Added ChromaDB integration with advanced document pipeline
  - ✅ Vector database for semantic document search
  - ✅ Smart document chunking and relationship mapping
  - ✅ Automated policy compliance checking
  - ✅ Multi-collection storage (documents, vectors, policies, relations)
  - ✅ Enhanced document editor with database auto-storage
  - ✅ Agent-ready architecture with context injection
  - ✅ Comprehensive analytics and health monitoring

### Original Browser-Use Features
- [x] **2025/01/26:** DeepSeek-r1 integration for enhanced deep thinking capabilities
- [x] **2025/01/10:** Docker Setup and persistent browser session support
- [x] **2025/01/06:** Modern, well-designed WebUI interface
