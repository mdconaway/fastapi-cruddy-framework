# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.x.x   | ✅         |
| 0.x.x   | ❌         |

---

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

Instead, use GitHub Security Advisories or contact the maintainer privately if a contact method is available.

When reporting a vulnerability, please include:

* A clear description of the issue
* Affected framework version(s)
* Steps to reproduce
* Example payloads or requests if applicable
* Potential impact
* Suggested mitigations or fixes if known

The maintainer will attempt to acknowledge reports within a reasonable timeframe.

---

## Scope

Security reports are especially appreciated for issues involving:

* Authentication or authorization bypass
* Policy-chain execution flaws
* CRUD route privilege escalation
* Relationship mutation vulnerabilities
* GraphQL query handling
* Websocket authentication or room isolation
* SQL query synthesis and filtering
* Unsafe deserialization or JSON parsing
* Datetime coercion and timezone handling
* Data exposure through automatic relationship loading
* Dependency-related vulnerabilities

---

## Disclosure Guidelines

Please avoid:

* Public disclosure before a fix is available
* Accessing or modifying data that does not belong to you
* Denial-of-service testing against public deployments
* Automated destructive scanning against example servers

Security research performed responsibly and in good faith is appreciated.

---

## Dependency Security

Users are encouraged to keep dependencies aligned with the versions and compatibility ranges declared in `pyproject.toml`.

This includes, but is not limited to:

- FastAPI
- SQLAlchemy
- SQLModel
- Pydantic
- Strawberry GraphQL
- Redis-related dependencies

---

## Framework Security Notes

Because `fastapi-cruddy-framework` automatically generates CRUD routes, relationship handlers, and query interfaces, application developers are responsible for:

* Proper authentication and authorization policies
* Restricting sensitive relationships
* Validating user input
* Applying sensible query limits
* Reviewing GraphQL exposure
* Securing websocket endpoints
* Preventing over-permissive data access

Misconfigured application policies may expose sensitive data even when the framework itself is functioning as intended.

---

## Supported Python Versions

Security support generally follows the Python and dependency versions declared in `pyproject.toml`.
