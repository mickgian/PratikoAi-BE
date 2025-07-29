# PratikoAI Version Management System

A comprehensive version coordination system for the PratikoAI project, managing dependencies and compatibility between the Kotlin Multiplatform frontend and FastAPI+LangGraph backend.

## 🎯 Overview

This system provides:

- **Shared Versioning**: Coordinated version tracking across frontend and backend services
- **Dependency Management**: Prevents deployment of incompatible versions
- **API Contract Validation**: Ensures API compatibility between service versions
- **CI/CD Integration**: Automated compatibility checking in deployment pipelines
- **Developer Tools**: CLI and APIs for version management operations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Version Management System                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │   Registry API  │  │  Compatibility   │  │   CLI Tools     │ │
│  │  (FastAPI)      │  │    Checker       │  │  (Python)       │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│           │                      │                      │        │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │   Database      │  │  Contract        │  │  GitHub Actions │ │
│  │  (PostgreSQL)   │  │  Validator       │  │  Integration    │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies
cd version-management
pip install -r requirements.txt

# Setup database
export VERSION_REGISTRY_DB_URL="postgresql://user:pass@localhost/version_registry"
python -c "from registry.database import init_database; init_database()"

# Start the registry API
python -m registry.api
```

### 2. Register Your First Version

```bash
# Interactive registration
python cli/version_cli.py register

# Or programmatically
curl -X POST http://localhost:8001/api/v1/versions/register \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "backend",
    "version": "1.0.0",
    "git_commit": "abc123",
    "git_branch": "main",
    "change_type": "minor"
  }'
```

### 3. Check Compatibility

```bash
# CLI compatibility check
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.0.0 \
  --environment production

# In CI/CD
python scripts/compatibility_checker.py \
  --service frontend-android \
  --version 2.1.0 \
  --environment staging \
  --output compatibility-report.json
```

## 📚 Documentation

- [🔧 Setup Guide](docs/setup.md) - Complete installation and configuration
- [👨‍💻 Developer Guide](docs/developer-guide.md) - Day-to-day usage patterns
- [🔗 API Reference](docs/api-reference.md) - REST API documentation
- [⚙️ CI/CD Integration](docs/cicd-integration.md) - GitHub Actions setup
- [🛠️ CLI Reference](docs/cli-reference.md) - Command-line tool usage
- [🔍 Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## 🎯 Service Types

The system supports these service types:

- `backend` - FastAPI+LangGraph backend service
- `frontend-android` - Android app (KMP)
- `frontend-ios` - iOS app (KMP)
- `frontend-desktop` - Desktop app (KMP)
- `frontend-web` - Web app (KMP)

## 🌍 Environments

- `development` - Local development
- `staging` - Staging environment
- `production` - Production environment

## 🔄 Version Lifecycle

```mermaid
graph TD
    A[Developer Creates PR] --> B[Version Generated]
    B --> C[Register in Registry]
    C --> D[Compatibility Check]
    D --> E{Compatible?}
    E -->|Yes| F[Deploy to Environment]
    E -->|No| G[Block Deployment]
    F --> H[Update Deployment Status]
    G --> I[Fix Compatibility Issues]
    I --> B
```

## 🔗 Examples

### Backend Version Registration

```python
from registry.database import init_database
from core.version_schema import ServiceType, ServiceVersion

# Initialize database
db = init_database()

# Register backend version
version = ServiceVersion(
    service_type=ServiceType.BACKEND,
    version="1.2.0",
    git_commit="def456",
    change_type="minor",
    dependencies=[
        # No dependencies for backend
    ]
)

db.register_version(version)
```

### Frontend Version with Backend Dependency

```python
from core.version_schema import ServiceType, ServiceVersion, VersionDependency

# Register frontend version that requires specific backend
frontend_version = ServiceVersion(
    service_type=ServiceType.FRONTEND_ANDROID,
    version="2.1.0",
    git_commit="ghi789",
    change_type="minor",
    dependencies=[
        VersionDependency(
            service_type=ServiceType.BACKEND,
            min_version="1.2.0",
            reason="Requires new user authentication API"
        )
    ]
)

db.register_version(frontend_version)
```

### Compatibility Check

```python
from scripts.compatibility_checker import CompatibilityChecker
from core.version_schema import ServiceType, Environment

checker = CompatibilityChecker(db)

# Check if frontend can be deployed
result = await checker.check_deployment_compatibility(
    ServiceType.FRONTEND_ANDROID,
    "2.1.0",
    Environment.PRODUCTION
)

print(f"Can deploy: {result['can_deploy']}")
print(f"Issues: {result['blocking_issues']}")
```

## 🔐 Configuration

### Environment Variables

```bash
# Registry API
VERSION_REGISTRY_URL=http://localhost:8001
VERSION_REGISTRY_TOKEN=your-api-token

# Database
VERSION_REGISTRY_DB_URL=postgresql://user:pass@localhost/version_registry

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
```

### GitHub Secrets

For CI/CD integration, set these secrets in your GitHub repositories:

- `VERSION_REGISTRY_URL` - URL of your version registry API
- `VERSION_REGISTRY_TOKEN` - Authentication token
- `VERSION_REGISTRY_DB_URL` - Database connection string

## 🚨 Common Workflows

### Daily Development

1. Create feature branch
2. Make changes
3. Create PR → automatic version generation and compatibility check
4. Address any compatibility issues
5. Merge → automatic deployment to staging

### Release Process

1. Create release branch
2. Run final compatibility checks
3. Deploy to production
4. Tag release in version registry

### Emergency Hotfix

1. Create hotfix branch from production
2. Make minimal changes
3. Fast-track compatibility check
4. Deploy with monitoring

## 🔧 Advanced Features

### API Contract Validation

The system automatically validates API contracts using OpenAPI specifications:

```python
from validation.contract_validator import APIContractValidator

validator = APIContractValidator()
result = await validator.validate_contract_evolution(old_contract, new_contract)

if not result.is_compatible:
    print("Breaking changes detected:")
    for change in result.breaking_changes:
        print(f"  - {change.description}")
```

### Custom Compatibility Rules

You can extend the compatibility checking with custom rules:

```python
from scripts.compatibility_checker import CompatibilityChecker

class CustomCompatibilityChecker(CompatibilityChecker):
    async def _check_custom_rules(self, service_type, version, environment):
        # Add your custom compatibility logic
        pass
```

## 📊 Monitoring

The system provides metrics for:

- Version registration rates
- Compatibility check results
- Deployment success/failure rates
- Breaking change frequencies

Integrate with your monitoring system using the provided APIs.

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure compatibility checks pass

## 📄 License

This version management system is part of the PratikoAI project.

---

**Need Help?** Check the [troubleshooting guide](docs/troubleshooting.md) or create an issue.