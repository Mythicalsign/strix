# Strix GitHub Actions Workflows

This document contains GitHub Actions workflow configurations for running Strix automatically. Copy the desired workflow to `.github/workflows/` in your repository.

---

## Table of Contents

1. [Full-Featured Strix Workflow](#full-featured-strix-workflow) - Complete workflow with all options
2. [Quick Scan Workflow](#quick-scan-workflow) - Simplified workflow for PR checks
3. [Scheduled Security Audit](#scheduled-security-audit) - Automated daily/weekly scans
4. [Manual Penetration Test](#manual-penetration-test) - On-demand deep scans
5. [StrixDB Sync Workflow](#strixdb-sync-workflow) - Sync artifacts to StrixDB

---

## Required Secrets

Before using these workflows, add the following secrets to your repository:

| Secret | Required | Description |
|--------|----------|-------------|
| `STRIX_LLM` | Yes | Model name (e.g., `openai/gpt-5`, `anthropic/claude-sonnet-4`) |
| `LLM_API_KEY` | Yes | API key for your LLM provider |
| `STRIXDB_TOKEN` | Optional | GitHub token for StrixDB repository access |
| `STRIXDB_REPO` | Optional | StrixDB repository (e.g., `username/StrixDB`) |
| `PERPLEXITY_API_KEY` | Optional | Perplexity API key for web search capabilities |
| `CLIPROXY_BASE_URL` | Optional | CLIProxyAPI server URL if using proxy mode |

---

## Full-Featured Strix Workflow

This is the complete workflow with all configuration options including custom prompts, timeframes, and StrixDB integration.

**File: `.github/workflows/strix-full.yml`**

```yaml
name: Strix Security Scan

on:
  # Manual trigger with inputs
  workflow_dispatch:
    inputs:
      target:
        description: 'Target to scan (URL, path, or repository)'
        required: true
        default: './'
        type: string
      prompt:
        description: 'Custom instructions for the AI agent'
        required: false
        default: ''
        type: string
      timeframe:
        description: 'Maximum runtime in minutes'
        required: false
        default: '60'
        type: string
      scan_mode:
        description: 'Scan mode'
        required: false
        default: 'deep'
        type: choice
        options:
          - quick
          - standard
          - deep
      enable_strixdb:
        description: 'Enable StrixDB artifact storage'
        required: false
        default: true
        type: boolean
  
  # Trigger on pull requests
  pull_request:
    branches: [main, master, develop]
  
  # Trigger on pushes to main
  push:
    branches: [main, master]

# Cancel in-progress runs for the same PR/branch
concurrency:
  group: strix-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

env:
  # Default configuration
  DEFAULT_TIMEFRAME: '60'
  DEFAULT_SCAN_MODE: 'standard'

jobs:
  strix-scan:
    name: Strix Security Scan
    runs-on: ubuntu-latest
    timeout-minutes: ${{ fromJSON(github.event.inputs.timeframe || '120') }}
    
    permissions:
      contents: read
      security-events: write
      pull-requests: write
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Strix
        run: |
          pip install strix-agent
          echo "Strix version: $(strix --version)"
      
      - name: Configure Environment
        run: |
          # Set timeframe (with enforcement)
          TIMEFRAME="${{ github.event.inputs.timeframe || env.DEFAULT_TIMEFRAME }}"
          echo "STRIX_TIMEOUT=${TIMEFRAME}m" >> $GITHUB_ENV
          
          # Calculate end time for the agent
          END_TIME=$(date -d "+${TIMEFRAME} minutes" +%s)
          echo "STRIX_END_TIME=${END_TIME}" >> $GITHUB_ENV
          
          # Set scan mode
          echo "SCAN_MODE=${{ github.event.inputs.scan_mode || env.DEFAULT_SCAN_MODE }}" >> $GITHUB_ENV
          
          # Configure StrixDB if enabled
          if [ "${{ github.event.inputs.enable_strixdb }}" == "true" ] || [ -n "${{ secrets.STRIXDB_TOKEN }}" ]; then
            echo "STRIXDB_ENABLED=true" >> $GITHUB_ENV
            echo "STRIXDB_REPO=${{ secrets.STRIXDB_REPO || 'StrixDB' }}" >> $GITHUB_ENV
          fi
      
      - name: Prepare Custom Instructions
        id: instructions
        run: |
          # Build instruction string
          INSTRUCTIONS=""
          
          # Add timeframe awareness
          TIMEFRAME="${{ github.event.inputs.timeframe || env.DEFAULT_TIMEFRAME }}"
          INSTRUCTIONS="[TIMEFRAME: You have ${TIMEFRAME} minutes to complete this task. Prioritize the most critical security checks first and ensure you finish with actionable findings.]"
          
          # Add custom prompt if provided
          if [ -n "${{ github.event.inputs.prompt }}" ]; then
            INSTRUCTIONS="${INSTRUCTIONS} [CUSTOM INSTRUCTIONS: ${{ github.event.inputs.prompt }}]"
          fi
          
          # Add StrixDB instructions if enabled
          if [ "${{ env.STRIXDB_ENABLED }}" == "true" ]; then
            INSTRUCTIONS="${INSTRUCTIONS} [STRIXDB: Save any useful scripts, tools, exploits, methods, or knowledge you discover to StrixDB for future use. Be an enthusiastic collector!]"
          fi
          
          # Add PR context if this is a pull request
          if [ "${{ github.event_name }}" == "pull_request" ]; then
            INSTRUCTIONS="${INSTRUCTIONS} [CONTEXT: This is a pull request review. Focus on security implications of the changed files.]"
          fi
          
          echo "instructions=${INSTRUCTIONS}" >> $GITHUB_OUTPUT
      
      - name: Run Strix Security Scan
        id: strix
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          STRIXDB_TOKEN: ${{ secrets.STRIXDB_TOKEN }}
          CLIPROXY_BASE_URL: ${{ secrets.CLIPROXY_BASE_URL }}
        run: |
          set +e  # Don't exit on error
          
          TARGET="${{ github.event.inputs.target || './' }}"
          
          # Run Strix with timeout enforcement
          timeout ${{ env.STRIX_TIMEOUT }} strix \
            --target "${TARGET}" \
            --scan-mode "${{ env.SCAN_MODE }}" \
            --non-interactive \
            --instruction "${{ steps.instructions.outputs.instructions }}" \
            2>&1 | tee strix_output.log
          
          EXIT_CODE=$?
          
          # Handle exit codes
          if [ $EXIT_CODE -eq 124 ]; then
            echo "Strix scan timed out after ${{ github.event.inputs.timeframe || env.DEFAULT_TIMEFRAME }} minutes"
            echo "timed_out=true" >> $GITHUB_OUTPUT
          elif [ $EXIT_CODE -eq 2 ]; then
            echo "Vulnerabilities found!"
            echo "vulnerabilities_found=true" >> $GITHUB_OUTPUT
          fi
          
          echo "exit_code=${EXIT_CODE}" >> $GITHUB_OUTPUT
      
      - name: Upload Scan Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: strix-results-${{ github.run_id }}
          path: |
            strix_runs/
            strix_output.log
          retention-days: 30
      
      - name: Comment on PR
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            
            let summary = '## 🦉 Strix Security Scan Results\n\n';
            
            const timedOut = '${{ steps.strix.outputs.timed_out }}' === 'true';
            const vulnsFound = '${{ steps.strix.outputs.vulnerabilities_found }}' === 'true';
            const exitCode = '${{ steps.strix.outputs.exit_code }}';
            
            if (timedOut) {
              summary += '⏱️ **Status:** Scan timed out\n\n';
              summary += 'The scan reached the maximum time limit. Partial results may be available in the artifacts.\n\n';
            } else if (vulnsFound) {
              summary += '🔴 **Status:** Vulnerabilities Found\n\n';
              summary += 'Security issues were identified. Please review the detailed report in the workflow artifacts.\n\n';
            } else {
              summary += '🟢 **Status:** Scan Completed\n\n';
              summary += 'No critical vulnerabilities were found.\n\n';
            }
            
            summary += `**Scan Mode:** ${{ env.SCAN_MODE }}\n`;
            summary += `**Timeframe:** ${{ github.event.inputs.timeframe || env.DEFAULT_TIMEFRAME }} minutes\n`;
            summary += `**Exit Code:** ${exitCode}\n\n`;
            
            summary += '📎 [View Full Results](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})\n';
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: summary
            });
      
      - name: Fail if Vulnerabilities Found
        if: steps.strix.outputs.vulnerabilities_found == 'true'
        run: |
          echo "Security vulnerabilities were found. Failing the workflow."
          exit 1
```

---

## Quick Scan Workflow

A simplified workflow for quick PR security checks.

**File: `.github/workflows/strix-quick.yml`**

```yaml
name: Strix Quick Scan

on:
  pull_request:
    branches: [main, master]

jobs:
  quick-scan:
    name: Quick Security Check
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Strix
        run: pip install strix-agent
      
      - name: Run Quick Scan
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          strix -n -t ./ --scan-mode quick \
            --instruction "[TIMEFRAME: 10 minutes max. Focus on critical vulnerabilities only.]"
```

---

## Scheduled Security Audit

Automated scheduled security scans.

**File: `.github/workflows/strix-scheduled.yml`**

```yaml
name: Scheduled Security Audit

on:
  schedule:
    # Run every Monday at 2 AM UTC
    - cron: '0 2 * * 1'
  workflow_dispatch:
    inputs:
      scan_mode:
        description: 'Scan mode'
        required: false
        default: 'deep'
        type: choice
        options:
          - standard
          - deep

jobs:
  security-audit:
    name: Weekly Security Audit
    runs-on: ubuntu-latest
    timeout-minutes: 180  # 3 hours for deep scan
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Strix
        run: pip install strix-agent
      
      - name: Run Deep Security Audit
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          STRIXDB_TOKEN: ${{ secrets.STRIXDB_TOKEN }}
          STRIXDB_REPO: ${{ secrets.STRIXDB_REPO }}
        run: |
          strix -n -t ./ \
            --scan-mode ${{ github.event.inputs.scan_mode || 'deep' }} \
            --instruction "[TIMEFRAME: 150 minutes. Perform comprehensive security audit. Save all findings and useful artifacts to StrixDB. Generate detailed compliance report.]"
      
      - name: Upload Audit Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: security-audit-${{ github.run_id }}
          path: strix_runs/
          retention-days: 90
      
      - name: Create Issue for Findings
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🔴 Security Audit Found Vulnerabilities',
              body: `## Weekly Security Audit Results\n\nThe automated security audit found potential vulnerabilities.\n\n**Run:** https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}\n\nPlease review the findings and take appropriate action.`,
              labels: ['security', 'automated']
            });
```

---

## Manual Penetration Test

On-demand deep penetration testing workflow.

**File: `.github/workflows/strix-pentest.yml`**

```yaml
name: Manual Penetration Test

on:
  workflow_dispatch:
    inputs:
      target:
        description: 'Target to test'
        required: true
        type: string
      prompt:
        description: 'Detailed instructions for the penetration test'
        required: true
        type: string
      timeframe:
        description: 'Maximum runtime in minutes'
        required: true
        default: '120'
        type: string
      credentials:
        description: 'Test credentials (format: user:pass) - stored securely'
        required: false
        type: string
      scope:
        description: 'Scope limitations (comma-separated paths to exclude)'
        required: false
        type: string

jobs:
  pentest:
    name: Penetration Test
    runs-on: ubuntu-latest
    timeout-minutes: ${{ fromJSON(github.event.inputs.timeframe) }}
    
    environment: security-testing
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Strix
        run: pip install strix-agent
      
      - name: Build Instructions
        id: build-instructions
        run: |
          INSTRUCTIONS="[TIMEFRAME: ${{ github.event.inputs.timeframe }} minutes]"
          INSTRUCTIONS="${INSTRUCTIONS} ${{ github.event.inputs.prompt }}"
          
          if [ -n "${{ github.event.inputs.credentials }}" ]; then
            INSTRUCTIONS="${INSTRUCTIONS} [CREDENTIALS: Use these credentials for authenticated testing: ${{ github.event.inputs.credentials }}]"
          fi
          
          if [ -n "${{ github.event.inputs.scope }}" ]; then
            INSTRUCTIONS="${INSTRUCTIONS} [SCOPE: Do NOT test these paths: ${{ github.event.inputs.scope }}]"
          fi
          
          INSTRUCTIONS="${INSTRUCTIONS} [STRIXDB: Save all exploits, PoCs, and useful findings to StrixDB]"
          
          echo "instructions=${INSTRUCTIONS}" >> $GITHUB_OUTPUT
      
      - name: Run Penetration Test
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          STRIXDB_TOKEN: ${{ secrets.STRIXDB_TOKEN }}
          STRIXDB_REPO: ${{ secrets.STRIXDB_REPO }}
        run: |
          strix -n \
            -t "${{ github.event.inputs.target }}" \
            --scan-mode deep \
            --instruction "${{ steps.build-instructions.outputs.instructions }}"
      
      - name: Upload Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pentest-results-${{ github.run_id }}
          path: strix_runs/
          retention-days: 90
```

---

## StrixDB Sync Workflow

Workflow to sync and organize StrixDB artifacts.

**File: `.github/workflows/strixdb-sync.yml`**

```yaml
name: StrixDB Sync

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        type: choice
        options:
          - sync
          - cleanup
          - export
      category:
        description: 'Category to process (all for everything)'
        required: false
        default: 'all'
        type: string

jobs:
  strixdb-sync:
    name: StrixDB Operations
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout StrixDB
        uses: actions/checkout@v4
        with:
          repository: ${{ secrets.STRIXDB_REPO }}
          token: ${{ secrets.STRIXDB_TOKEN }}
          path: strixdb
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Process StrixDB
        working-directory: strixdb
        run: |
          case "${{ github.event.inputs.action }}" in
            sync)
              echo "Syncing StrixDB..."
              # Update index files
              for dir in scripts exploits knowledge libraries sources methods tools configs; do
                if [ -d "$dir" ]; then
                  echo "## ${dir^}" > "${dir}/README.md"
                  echo "" >> "${dir}/README.md"
                  echo "| Name | Description | Tags |" >> "${dir}/README.md"
                  echo "|------|-------------|------|" >> "${dir}/README.md"
                  find "$dir" -name "*.json" -exec cat {} \; | jq -r '"\(.name) | \(.description) | \(.tags | join(", "))"' >> "${dir}/README.md" 2>/dev/null || true
                fi
              done
              ;;
            cleanup)
              echo "Cleaning up old/duplicate entries..."
              # Add cleanup logic
              ;;
            export)
              echo "Exporting StrixDB..."
              tar -czvf ../strixdb-export.tar.gz .
              ;;
          esac
      
      - name: Commit Changes
        if: github.event.inputs.action != 'export'
        working-directory: strixdb
        run: |
          git config user.name "StrixDB Bot"
          git config user.email "strixdb@users.noreply.github.com"
          git add -A
          git diff --staged --quiet || git commit -m "StrixDB: ${{ github.event.inputs.action }} operation"
          git push
      
      - name: Upload Export
        if: github.event.inputs.action == 'export'
        uses: actions/upload-artifact@v4
        with:
          name: strixdb-export
          path: strixdb-export.tar.gz
```

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `STRIX_LLM` | LLM model identifier | Yes |
| `LLM_API_KEY` | API key for LLM provider | Yes |
| `LLM_API_BASE` | Custom API base URL | No |
| `PERPLEXITY_API_KEY` | Perplexity API key for web search | No |
| `STRIXDB_TOKEN` | GitHub token for StrixDB | No |
| `STRIXDB_REPO` | StrixDB repository name | No |
| `STRIXDB_BRANCH` | StrixDB branch (default: main) | No |
| `CLIPROXY_ENABLED` | Enable CLIProxyAPI mode | No |
| `CLIPROXY_BASE_URL` | CLIProxyAPI server URL | No |

---

## Tips for Effective Workflows

### Timeframe Guidelines

| Scan Type | Recommended Time | Use Case |
|-----------|------------------|----------|
| Quick | 10-15 min | PR checks, CI gates |
| Standard | 30-60 min | Regular security checks |
| Deep | 2-4 hours | Full penetration tests |

### Writing Effective Prompts

Good prompts should include:

1. **Objective**: What you want to achieve
2. **Focus Areas**: Specific vulnerability types to prioritize
3. **Context**: Application type, technology stack
4. **Constraints**: What NOT to test
5. **Output Requirements**: What format for findings

**Example:**
```
Focus on authentication bypass and IDOR vulnerabilities in the /api/* endpoints. 
The application uses JWT tokens. Do NOT test /api/health or /api/status endpoints.
Provide detailed PoCs for any findings and save useful bypass techniques to StrixDB.
```

### Security Best Practices

1. **Use environments** for sensitive workflows
2. **Limit permissions** to minimum required
3. **Store credentials in secrets**, never in workflow files
4. **Set reasonable timeouts** to prevent runaway costs
5. **Review artifacts** before making them public
