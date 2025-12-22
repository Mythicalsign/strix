<p align="center">
  <a href="https://usestrix.com/">
    <img src=".github/logo.png" width="150" alt="Strix Logo">
  </a>
</p>

<h1 align="center">Strix</h1>

<h2 align="center">Open-source AI Hackers to secure your Apps</h2>

<div align="center">

[![Python](https://img.shields.io/pypi/pyversions/strix-agent?color=3776AB)](https://pypi.org/project/strix-agent/)
[![PyPI](https://img.shields.io/pypi/v/strix-agent?color=10b981)](https://pypi.org/project/strix-agent/)
![PyPI Downloads](https://static.pepy.tech/personalized-badge/strix-agent?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=RED&left_text=Downloads)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[![GitHub Stars](https://img.shields.io/github/stars/usestrix/strix)](https://github.com/usestrix/strix)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&logoColor=white)](https://discord.gg/YjKFvEZSdZ)
[![Website](https://img.shields.io/badge/Website-usestrix.com-2d3748.svg)](https://usestrix.com)

<a href="https://trendshift.io/repositories/15362" target="_blank"><img src="https://trendshift.io/api/badge/repositories/15362" alt="usestrix%2Fstrix | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>


[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/usestrix/strix)

</div>

<br>

<div align="center">
  <img src=".github/screenshot.png" alt="Strix Demo" width="800" style="border-radius: 16px;">
</div>

<br>

> [!TIP]
> **New!** Strix now integrates seamlessly with GitHub Actions and CI/CD pipelines. Automatically scan for vulnerabilities on every pull request and block insecure code before it reaches production!

---

## 🦉 Strix Overview

Strix are autonomous AI agents that act just like real hackers - they run your code dynamically, find vulnerabilities, and validate them through actual proof-of-concepts. Built for developers and security teams who need fast, accurate security testing without the overhead of manual pentesting or the false positives of static analysis tools.

**Key Capabilities:**

- 🔧 **Full hacker toolkit** out of the box
- 🤝 **Teams of agents** that collaborate and scale
- ✅ **Real validation** with PoCs, not false positives
- 💻 **Developer‑first** CLI with actionable reports
- 🔄 **Auto‑fix & reporting** to accelerate remediation


## 🎯 Use Cases

- **Application Security Testing** - Detect and validate critical vulnerabilities in your applications
- **Rapid Penetration Testing** - Get penetration tests done in hours, not weeks, with compliance reports
- **Bug Bounty Automation** - Automate bug bounty research and generate PoCs for faster reporting
- **CI/CD Integration** - Run tests in CI/CD to block vulnerabilities before reaching production

---

## 🆕 New Features (Enhanced Edition)

This enhanced version of Strix includes significant new capabilities:

### 🔐 Root Terminal Access

The Main AI agent now has **full root/sudo access** by default, enabling:

- **Package Installation**: Install any system packages, libraries, or tools via `apt-get`, `pip`, `npm`
- **Database Management**: Create and manage MySQL, PostgreSQL, SQLite, and MongoDB databases
- **Service Control**: Start, stop, and manage system services
- **Script Execution**: Run scripts with elevated privileges
- **Multiple Root Terminals**: Up to **7 concurrent root terminals** for parallel operations

```python
# Available tools:
- root_execute(command, timeout, terminal_id)  # Execute with root privileges
- create_root_terminal(name)                    # Create new root terminal (max 7)
- install_package(packages)                     # Install apt packages
- install_pip_package(packages)                 # Install Python packages
- install_npm_package(packages)                 # Install Node.js packages
- create_database(db_type, db_name, user, password)  # Create databases
- manage_service(service_name, action)          # Control services
```

### 🤖 Custom Sub-Agent System

Create highly customizable sub-agents with advanced configuration:

- **Root Access for Sub-Agents**: Grant root terminal access to any sub-agent
- **Custom Capabilities**: Configure specific tool access per agent
- **Priority Levels**: Set execution priority (critical, high, medium, low)
- **Custom Instructions**: Inject specialized instructions
- **Dynamic Access Control**: Grant/revoke root access at runtime

```python
# Create a root-enabled agent
create_custom_agent(
    task="Install and configure security tools",
    name="Security Setup Agent",
    root_access=True,
    priority="high",
    capabilities=["root_terminal", "terminal", "file_edit"]
)

# Or use the convenience function
create_root_enabled_agent(
    task="Set up the testing environment",
    name="Environment Agent"
)

# Grant root access dynamically
grant_root_access(target_agent_id="agent_abc123")
```

### 📚 Advanced Knowledge Management

A significantly enhanced knowledge and notes system with:

- **Hierarchical Organization**: Collections and nested folders
- **Entry Linking**: Typed relationships (related_to, depends_on, blocks, references, etc.)
- **Priority Levels**: Critical, high, medium, low
- **Full-Text Search**: Relevance-ranked search with filtering
- **Templates**: Pre-built templates for vulnerabilities, credentials, endpoints, etc.
- **Version History**: Track changes with rollback capability
- **Export/Import**: JSON and Markdown export
- **Cross-Agent Sharing**: Share knowledge between agents

```python
# Create and link entries
create_knowledge_entry(
    title="SQL Injection in Login",
    content="Found SQLi vulnerability...",
    category="findings",
    priority="critical",
    tags=["sqli", "authentication"]
)

link_entries(source_id, target_id, relationship_type="confirms")

# Advanced search
advanced_search(
    query="SQL injection",
    category=["findings"],
    priority=["critical", "high"],
    created_after="2024-01-01"
)

# Use templates
create_from_template("vulnerability", {
    "title": "XSS in Search",
    "severity": "high",
    "poc": "<script>alert(1)</script>"
})
```

### 🎭 Advanced Multi-Agent Orchestration

Significantly improved coordination capabilities:

#### Task Management
- **Priority Queue**: Tasks ordered by priority with dependency resolution
- **Task Dependencies**: Create task chains with circular dependency detection
- **Auto-Assignment**: Automatic load-balanced task distribution
- **Status Tracking**: Full lifecycle tracking (pending → assigned → in_progress → completed)

#### Workload Management
- **Capacity Control**: Set max concurrent tasks per agent (1-20)
- **Utilization Monitoring**: Track agent workload percentages
- **Load Balancing**: Automatic distribution to least busy agents

#### Team Management
- **Create Teams**: Organize agents into functional teams
- **Role Assignment**: Assign roles (member, specialist, coordinator)
- **Team Coordination**: Broadcast messages to team members

#### Advanced Coordination
- **Broadcast Messaging**: Send to all agents, specific agents, or teams
- **Coordination Requests**: Request assistance, review, approval, or handoff
- **Synchronization Points**: Create checkpoints for multi-agent sync
- **Resource Management**: Allocate and manage shared resources

#### Workflow Automation
- **Workflow Definition**: Create multi-step workflows with dependencies
- **Workflow Execution**: Execute workflows with automatic task creation
- **Pause/Resume**: Control workflow execution

#### Monitoring Dashboard
- **System Metrics**: Real-time agent and task statistics
- **Agent Health**: Health status (healthy, busy, overloaded, degraded, critical)
- **Dashboard View**: Comprehensive orchestration overview

```python
# Create a workflow
create_workflow(
    name="Security Assessment",
    description="Complete security assessment workflow",
    steps=[
        {"name": "Recon", "task_template": "Perform reconnaissance"},
        {"name": "Scan", "task_template": "Run vulnerability scan", "depends_on": ["Recon"]},
        {"name": "Exploit", "task_template": "Validate vulnerabilities", "depends_on": ["Scan"]},
        {"name": "Report", "task_template": "Generate report", "depends_on": ["Exploit"]}
    ]
)

# Create a team
create_agent_team(
    name="Exploitation Team",
    initial_members=["agent_abc", "agent_def"]
)

# Broadcast to team
broadcast_message(
    message="Focus on authentication endpoints",
    team_id="team_xyz",
    priority="high"
)

# Get orchestration dashboard
get_orchestration_dashboard()
```

---

## 🚀 Quick Start

**Prerequisites:**
- Docker (running)
- An LLM provider key (e.g. [get OpenAI API key](https://platform.openai.com/api-keys) or use a local LLM)

### Installation & First Scan

```bash
# Install Strix
curl -sSL https://strix.ai/install | bash

# Or via pipx
pipx install strix-agent

# Configure your AI provider
export STRIX_LLM="openai/gpt-5"
export LLM_API_KEY="your-api-key"

# Run your first security assessment
strix --target ./app-directory
```

> [!NOTE]
> First run automatically pulls the sandbox Docker image. Results are saved to `strix_runs/<run-name>`

## ☁️ Run Strix in Cloud

Want to skip the local setup, API keys, and unpredictable LLM costs? Run the hosted cloud version of Strix at **[app.usestrix.com](https://usestrix.com)**.

Launch a scan in just a few minutes—no setup or configuration required—and you'll get:

- **A full pentest report** with validated findings and clear remediation steps
- **Shareable dashboards** your team can use to track fixes over time
- **CI/CD and GitHub integrations** to block risky changes before production
- **Continuous monitoring** so new vulnerabilities are caught quickly

[**Run your first pentest now →**](https://usestrix.com)

---

## ✨ Features

### 🛠️ Agentic Security Tools

Strix agents come equipped with a comprehensive security testing toolkit:

- **Full HTTP Proxy** - Full request/response manipulation and analysis
- **Browser Automation** - Multi-tab browser for testing of XSS, CSRF, auth flows
- **Terminal Environments** - Interactive shells for command execution and testing
- **Root Terminal Access** - Full sudo/root access for privileged operations (NEW!)
- **Python Runtime** - Custom exploit development and validation
- **Reconnaissance** - Automated OSINT and attack surface mapping
- **Code Analysis** - Static and dynamic analysis capabilities
- **Knowledge Management** - Structured findings with linking and search (ENHANCED!)

### 🎯 Comprehensive Vulnerability Detection

Strix can identify and validate a wide range of security vulnerabilities:

- **Access Control** - IDOR, privilege escalation, auth bypass
- **Injection Attacks** - SQL, NoSQL, command injection
- **Server-Side** - SSRF, XXE, deserialization flaws
- **Client-Side** - XSS, prototype pollution, DOM vulnerabilities
- **Business Logic** - Race conditions, workflow manipulation
- **Authentication** - JWT vulnerabilities, session management
- **Infrastructure** - Misconfigurations, exposed services

### 🕸️ Graph of Agents

Advanced multi-agent orchestration for comprehensive security testing:

- **Distributed Workflows** - Specialized agents for different attacks and assets
- **Scalable Testing** - Parallel execution for fast comprehensive coverage
- **Dynamic Coordination** - Agents collaborate and share discoveries
- **Priority-Based Scheduling** - Task prioritization with dependency resolution (NEW!)
- **Load Balancing** - Automatic workload distribution (NEW!)
- **Team Management** - Organize agents into functional teams (NEW!)
- **Workflow Automation** - Define and execute multi-step workflows (NEW!)

---

## 💻 Usage Examples

### Basic Usage

```bash
# Scan a local codebase
strix --target ./app-directory

# Security review of a GitHub repository
strix --target https://github.com/org/repo

# Black-box web application assessment
strix --target https://your-app.com
```

### Advanced Testing Scenarios

```bash
# Grey-box authenticated testing
strix --target https://your-app.com --instruction "Perform authenticated testing using credentials: user:pass"

# Multi-target testing (source code + deployed app)
strix -t https://github.com/org/app -t https://your-app.com

# Focused testing with custom instructions
strix --target api.your-app.com --instruction "Focus on business logic flaws and IDOR vulnerabilities"

# Provide detailed instructions through file (e.g., rules of engagement, scope, exclusions)
strix --target api.your-app.com --instruction-file ./instruction.md
```

### 🤖 Headless Mode

Run Strix programmatically without interactive UI using the `-n/--non-interactive` flag—perfect for servers and automated jobs. The CLI prints real-time vulnerability findings, and the final report before exiting. Exits with non-zero code when vulnerabilities are found.

```bash
strix -n --target https://your-app.com
```

### 🔄 CI/CD (GitHub Actions)

Strix can be added to your pipeline to run a security test on pull requests with a lightweight GitHub Actions workflow:

```yaml
name: strix-penetration-test

on:
  pull_request:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install Strix
        run: curl -sSL https://strix.ai/install | bash

      - name: Run Strix
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}

        run: strix -n -t ./ --scan-mode quick
```

### ⚙️ Configuration

```bash
export STRIX_LLM="openai/gpt-5"
export LLM_API_KEY="your-api-key"

# Optional
export LLM_API_BASE="your-api-base-url"  # if using a local model, e.g. Ollama, LMStudio
export PERPLEXITY_API_KEY="your-api-key"  # for search capabilities
```

[OpenAI's GPT-5](https://openai.com/api/) (`openai/gpt-5`) and [Anthropic's Claude Sonnet 4.5](https://claude.com/platform/api) (`anthropic/claude-sonnet-4-5`) are the recommended models for best results with Strix. We also support many [other options](https://docs.litellm.ai/docs/providers), including cloud and local models, though their performance and reliability may vary.

## 🤝 Contributing

We welcome contributions of code, docs, and new prompt modules - check out our [Contributing Guide](CONTRIBUTING.md) to get started or open a [pull request](https://github.com/usestrix/strix/pulls)/[issue](https://github.com/usestrix/strix/issues).

## 👥 Join Our Community

Have questions? Found a bug? Want to contribute? **[Join our Discord!](https://discord.gg/YjKFvEZSdZ)**

## 🌟 Support the Project

**Love Strix?** Give us a ⭐ on GitHub!
## 🙏 Acknowledgements

Strix builds on the incredible work of open-source projects like [LiteLLM](https://github.com/BerriAI/litellm), [Caido](https://github.com/caido/caido), [ProjectDiscovery](https://github.com/projectdiscovery), [Playwright](https://github.com/microsoft/playwright), and [Textual](https://github.com/Textualize/textual). Huge thanks to their maintainers!


> [!WARNING]
> Only test apps you own or have permission to test. You are responsible for using Strix ethically and legally.

</div>

---

## 📁 New Files and Modules

### Root Terminal Module (`strix/tools/root_terminal/`)
- `__init__.py` - Module exports
- `root_terminal_actions.py` - Tool functions for root operations
- `root_terminal_actions_schema.xml` - XML schema for tools
- `root_terminal_manager.py` - Manager for multiple root terminals
- `root_terminal_session.py` - Individual terminal session handling

### Custom Agents Module (`strix/tools/custom_agents/`)
- `__init__.py` - Module exports
- `custom_agent_actions.py` - Custom agent creation and management
- `custom_agent_actions_schema.xml` - XML schema for tools

### Knowledge Module (`strix/tools/knowledge/`)
- `__init__.py` - Module exports
- `knowledge_actions.py` - Advanced knowledge management system
- `knowledge_actions_schema.xml` - XML schema for tools

### Orchestration Module (`strix/tools/orchestration/`)
- `__init__.py` - Module exports
- `orchestration_actions.py` - Multi-agent orchestration system
- `orchestration_actions_schema.xml` - XML schema for tools

### Modified Files
- `strix/tools/__init__.py` - Updated to include new modules
