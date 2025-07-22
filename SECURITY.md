# Security Policy

## Overview

CloudZero takes the security of the LiteLLM CloudZero ETL project seriously. We appreciate the security research community's efforts to help us maintain the security of our open source projects and protect our users.

## Supported Versions

We provide security updates for the following versions of the LiteLLM CloudZero ETL tool:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it responsibly by following these guidelines:

### Preferred Reporting Method

**Email**: Send vulnerability reports to [security@cloudzero.com](mailto:security@cloudzero.com)

### What to Include

When reporting a security vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: Potential impact and severity assessment
3. **Steps to Reproduce**: Detailed steps to reproduce the vulnerability
4. **Proof of Concept**: Working proof-of-concept code (if applicable)
5. **Affected Versions**: Which versions are affected
6. **Suggested Mitigation**: Any suggested fixes or workarounds
7. **Contact Information**: How we can reach you for follow-up questions

### Example Report Template

```
Subject: [SECURITY] Vulnerability in LiteLLM CloudZero ETL

Vulnerability Type: [e.g., SQL Injection, Path Traversal, etc.]
Affected Component: [e.g., database.py, cli.py, etc.]
Severity: [High/Medium/Low]

Description:
[Detailed description of the vulnerability]

Steps to Reproduce:
1. [First step]
2. [Second step]
3. [etc.]

Impact:
[Description of potential impact]

Proof of Concept:
[Code or commands demonstrating the vulnerability]

Suggested Fix:
[Any suggestions for fixing the vulnerability]

Contact: [Your email address]
```

### Response Timeline

We are committed to responding to security reports in a timely manner:

- **Initial Response**: Within 48 hours of receiving your report
- **Assessment**: Within 5 business days, we will provide an initial assessment
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days
- **Disclosure**: After a fix is available, we will coordinate disclosure timing with you

## Security Best Practices

### For Users

When using the LiteLLM CloudZero ETL tool:

1. **Secure Configuration**
   - Store database credentials securely in `~/.ll2cz/config.yml`
   - Use strong passwords for database connections
   - Limit database user permissions to minimum required access
   - Regularly rotate API keys and database credentials

2. **Network Security**
   - Use encrypted connections (SSL/TLS) for database connections
   - Ensure CloudZero API calls use HTTPS
   - Run the tool in secure network environments
   - Consider using VPN or private networks for database access

3. **Data Protection**
   - Be cautious when using `--test` mode in shared environments
   - Avoid logging sensitive data in production
   - Regularly clean up temporary files and cache data
   - Follow your organization's data retention policies

4. **System Security**
   - Keep Python and dependencies updated
   - Use virtual environments to isolate dependencies
   - Run with minimal required system privileges
   - Monitor system logs for unusual activity

### For Contributors

When contributing to the project:

1. **Code Security**
   - Never commit secrets, API keys, or credentials
   - Use parameterized queries to prevent SQL injection
   - Validate and sanitize all user inputs
   - Follow secure coding practices and guidelines

2. **Dependency Management**
   - Keep dependencies updated to latest secure versions
   - Regularly audit dependencies for known vulnerabilities
   - Use dependency scanning tools when available
   - Document security-relevant dependency choices

3. **Testing**
   - Include security testing in your test cases
   - Test error handling and edge cases
   - Verify that sensitive data is not exposed in logs or outputs
   - Test authentication and authorization mechanisms

## Known Security Considerations

### Data Sensitivity

This tool handles potentially sensitive information:

- **Database Credentials**: PostgreSQL connection strings
- **API Keys**: CloudZero API credentials
- **Usage Data**: LiteLLM usage metrics and costs
- **User Information**: Team and user identifiers

### Mitigations in Place

1. **Configuration Security**
   - Config files use restrictive file permissions
   - API keys are masked in display output
   - No hardcoded credentials in source code
   - Comprehensive .gitignore to prevent credential commits

2. **Data Handling**
   - Secure HTTP connections for API calls
   - Local SQLite cache with appropriate file permissions
   - No sensitive data in error messages or logs
   - Memory-safe data processing with Polars

3. **Input Validation**
   - Database connection string validation
   - API response validation and error handling
   - File path validation for output operations
   - User input sanitization in CLI commands

## Vulnerability Disclosure Policy

### Our Commitment

- We will acknowledge receipt of vulnerability reports within 48 hours
- We will provide regular updates on our progress
- We will credit researchers who responsibly disclose vulnerabilities (unless they prefer to remain anonymous)
- We will not pursue legal action against researchers who follow our responsible disclosure policy

### Coordinated Disclosure

We prefer coordinated disclosure to ensure:

- Adequate time to develop and test fixes
- Coordination with downstream users and integrators
- Proper communication to the community about security updates
- Protection of users during the vulnerability window

### Recognition

We maintain a security researchers acknowledgment section to recognize those who help improve our security:

#### Security Researchers

*We thank the following security researchers for their responsible disclosure of vulnerabilities:*

<!-- This section will be updated as vulnerabilities are reported and fixed -->

## Additional Resources

### Security Documentation

- [CloudZero Security Page](https://www.cloudzero.com/security)
- [Python Security Guidelines](https://python.org/dev/security/)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)

### Security Tools

Consider using these tools for security analysis:

- **Static Analysis**: bandit, semgrep
- **Dependency Scanning**: safety, pip-audit
- **Secret Scanning**: truffleHog, git-secrets
- **Container Scanning**: trivy, clair (if containerized)

## Contact Information

For security-related questions or concerns:

- **Security Team**: [security@cloudzero.com](mailto:security@cloudzero.com)
- **General Support**: [support@cloudzero.com](mailto:support@cloudzero.com)
- **Project Maintainers**: See [CONTRIBUTING.md](CONTRIBUTING.md) for contact information

## Legal

This security policy is subject to CloudZero's terms of service and privacy policy. By participating in our security research program, you agree to comply with all applicable laws and regulations.

---

**Last Updated**: January 2025

We reserve the right to update this security policy at any time. Material changes will be communicated through appropriate channels.