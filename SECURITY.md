# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

Only the latest release receives security fixes. If you are running an older version, please upgrade first.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately via GitHub's built-in vulnerability reporting:

1. Go to the [Security tab](https://github.com/Maneesh-Relanto/Prompt-Run/security) of this repository.
2. Click **"Report a vulnerability"**.
3. Fill in the details — what you found, how to reproduce it, and the potential impact.

You can also email the maintainer directly. A reply will be sent within **48 hours** and a fix will be prioritised accordingly.

## What to Report

- Vulnerabilities that allow reading or exfiltrating API keys
- Path traversal or arbitrary file read/write in `.prompt` file parsing
- Code injection through variable substitution
- Dependency vulnerabilities with a realistic exploitation path

## What is Out of Scope

- Issues in third-party AI provider SDKs (Anthropic, OpenAI, Ollama) — report those upstream
- "prompt-run sends my prompt to OpenAI" — this is intentional and documented behavior
- Social engineering or phishing attacks

## Disclosure Policy

Once a fix is available and released:

- A security advisory will be published on GitHub.
- The fix will be noted in [CHANGELOG.md](CHANGELOG.md).
- Credit will be given to the reporter unless they prefer to remain anonymous.
