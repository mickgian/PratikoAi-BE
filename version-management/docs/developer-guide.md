# 👨‍💻 Developer Guide

This guide covers day-to-day usage of the PratikoAI Version Management System for developers working on the frontend and backend services.

## 🎯 Quick Reference

| Task | Command | When to Use |
|------|---------|-------------|
| Check compatibility | `python scripts/compatibility_checker.py --service backend --version 1.2.0 --environment staging` | Before deploying |
| Register version | `python cli/version_cli.py register` | After merging features |
| List versions | `python cli/version_cli.py list --service backend` | Check release history |
| View deployment status | `python cli/version_cli.py deployments --environment production` | Monitor deployments |

## 🔄 Development Workflow

### 1. Feature Development

When starting a new feature:

```bash
# Create feature branch
git checkout -b feature/user-authentication

# Make your changes...
# No version management needed during development
```

### 2. Pre-Merge Checks

Before creating a PR:

```bash
# Check if your changes might cause compatibility issues
python scripts/compatibility_checker.py \
  --service backend \
  --version $(git rev-parse --short HEAD) \
  --environment development
```

### 3. Pull Request Process

When you create a PR, the GitHub Actions workflow automatically:

1. **Generates a version** based on your changes
2. **Registers the version** in the registry
3. **Checks compatibility** with deployed services
4. **Comments on the PR** with compatibility results

Example PR comment:
```markdown
## 📋 Version Compatibility Report

**Service:** backend v20240115-abc123  
**Environment:** staging  
**Status:** ✅ Compatible  
**Compatibility Level:** fully_compatible

### 💡 Recommendations
- Review all changes carefully before production deployment
```

### 4. Post-Merge Deployment

After merging to `main` or `develop`:

1. **Automatic deployment** to staging/development
2. **Version tracking** in the registry
3. **Compatibility validation** for dependent services

## 🎨 Frontend Development

### Android/iOS/Desktop Development

```bash
# Check backend compatibility before implementing new features
python scripts/compatibility_checker.py \
  --service frontend-android \
  --version 2.1.0 \
  --environment staging \
  --targets backend

# Register a new frontend version
python cli/version_cli.py register
# Select: frontend-android
# Version: 2.1.0
# Backend dependency: 1.2.0+
```

### Multi-Platform Considerations

Different platforms may have different backend requirements:

```python
# In your KMP configuration file
backend_requirements = {
    "android": "1.2.0",      # Latest features
    "ios": "1.1.0",          # Stable version
    "desktop": "1.2.0",      # Latest features
    "web": "1.0.0"           # Minimal requirements
}
```

### Testing Frontend Changes

```bash
# Test against specific backend version
export BACKEND_VERSION=1.2.0
./gradlew testDebugUnitTest

# Validate API contract compatibility
python scripts/compatibility_checker.py \
  --service frontend-android \
  --version $(grep version gradle.properties | cut -d'=' -f2) \
  --environment development
```

## ⚙️ Backend Development

### API Changes

When modifying APIs, always consider compatibility:

```python
# Good: Adding optional field
@dataclass
class UserResponse:
    id: int
    name: str
    email: str
    created_at: datetime = None  # Optional, backward compatible

# Bad: Removing existing field
@dataclass
class UserResponse:
    id: int
    # name: str  # BREAKING: Removed field
    email: str
```

### Version Registration

```bash
# Register backend version with API contract
python cli/version_cli.py register
# The system will automatically:
# 1. Generate OpenAPI specification
# 2. Compare with previous version
# 3. Detect breaking changes
# 4. Register with contract information
```

### Breaking Change Process

When you must make breaking changes:

1. **Plan the change** with frontend teams
2. **Version the API** (e.g., `/api/v2/users`)
3. **Deprecate old endpoints** gradually
4. **Coordinate deployment** timing

```python
# Mark endpoint as deprecated
@app.get("/api/v1/users/{user_id}", deprecated=True)
async def get_user_v1(user_id: int):
    """
    Deprecated: Use /api/v2/users/{user_id} instead.
    Will be removed in version 2.0.0.
    """
    return await get_user_legacy(user_id)

@app.get("/api/v2/users/{user_id}")
async def get_user_v2(user_id: int):
    """New user endpoint with enhanced response."""
    return await get_user_enhanced(user_id)
```

## 🔍 Debugging and Troubleshooting

### Common Issues

#### 1. Compatibility Check Fails

```bash
# Get detailed compatibility report
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment production \
  --output detailed-report.json

# Review the issues
cat detailed-report.json | jq '.blocking_issues'
```

#### 2. Deployment Blocked

```bash
# Check current deployment status
python cli/version_cli.py deployments --environment production

# Validate specific deployment
python cli/version_cli.py validate backend 1.3.0 production
```

#### 3. Version Registration Issues

```bash
# Check if version already exists
python cli/version_cli.py show backend 1.3.0

# List recent versions
python cli/version_cli.py list --service backend --limit 10
```

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
export VERSION_MANAGEMENT_DEBUG=true

# Run commands with detailed output
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment production \
  --output debug-report.json
```

## 🚀 Release Management

### Staging Release

```bash
# 1. Ensure all compatibility checks pass
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment staging

# 2. Register the release version
python cli/version_cli.py register
# Mark as: minor/major release
# Add release notes

# 3. Deploy to staging (handled by CI/CD)
git push origin develop
```

### Production Release

```bash
# 1. Final compatibility validation
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment production \
  --fail-on-warnings

# 2. Coordinate with frontend team
# Ensure frontend versions are compatible

# 3. Deploy to production
git checkout main
git merge develop
git tag v1.3.0
git push origin main --tags
```

### Rollback Process

If issues are detected after deployment:

```bash
# 1. Check deployment history
python cli/version_cli.py deployments --environment production

# 2. Identify last known good version
python cli/version_cli.py list --service backend --limit 5

# 3. Validate rollback compatibility
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.2.5 \
  --environment production

# 4. Execute rollback (via CI/CD or manual process)
```

## 📊 Monitoring and Observability

### Version Metrics

```bash
# Get version statistics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/v1/stats

# Example response:
{
  "total_versions": 142,
  "services": {
    "backend": 45,
    "frontend-android": 32,
    "frontend-ios": 28,
    "frontend-web": 37
  },
  "compatibility_checks": {
    "total": 1205,
    "passed": 1156,
    "failed": 49
  }
}
```

### Deployment Tracking

```bash
# Monitor deployment patterns
python cli/version_cli.py deployments

# Check compatibility trends
python -c "
from registry.database import init_database
db = init_database()
stats = db.get_compatibility_stats(days=30)
print(f'Success rate: {stats.success_rate:.1%}')
print(f'Average resolution time: {stats.avg_resolution_hours:.1f}h')
"
```

## 🔧 Advanced Usage

### Custom Compatibility Rules

Create custom compatibility checkers:

```python
# custom_checker.py
from scripts.compatibility_checker import CompatibilityChecker
from core.version_schema import ServiceType, Environment

class ProjectCompatibilityChecker(CompatibilityChecker):
    async def _check_custom_rules(self, service_type: ServiceType, 
                                 version: str, environment: Environment):
        """Add project-specific compatibility rules."""
        
        # Example: Block deployment on Fridays in production
        if environment == Environment.PRODUCTION:
            import datetime
            if datetime.datetime.now().weekday() == 4:  # Friday
                return {
                    "blocking_issues": ["No production deployments on Fridays"],
                    "can_deploy": False
                }
        
        return {"can_deploy": True, "blocking_issues": []}

# Use custom checker
checker = ProjectCompatibilityChecker(db)
result = await checker.check_deployment_compatibility(...)
```

### API Integration

Integrate version management into your applications:

```python
# FastAPI middleware example
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

@app.middleware("http")
async def version_compatibility_middleware(request: Request, call_next):
    # Check if request is from compatible frontend version
    frontend_version = request.headers.get("X-Frontend-Version")
    backend_version = "1.3.0"  # Current backend version
    
    if frontend_version:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/api/v1/compatibility/check",
                json={
                    "source_service": "frontend-android",
                    "source_version": frontend_version,
                    "target_service": "backend",
                    "target_version": backend_version
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["compatibility_level"] == "incompatible":
                    return JSONResponse(
                        status_code=426,
                        content={"error": "Frontend version incompatible"}
                    )
    
    return await call_next(request)
```

### Batch Operations

Process multiple versions:

```bash
# Register multiple versions from Git history
git log --oneline main..develop | while read commit message; do
  python cli/version_cli.py register \
    --service backend \
    --version "dev-$(echo $commit | cut -c1-7)" \
    --git-commit "$commit" \
    --change-type patch \
    --automated
done

# Batch compatibility check
for version in 1.2.0 1.2.1 1.2.2; do
  echo "Checking version $version..."
  python scripts/compatibility_checker.py \
    --service backend \
    --version $version \
    --environment production \
    --quiet
done
```

## 🎓 Best Practices

### Version Naming

- **Backend**: Semantic versioning (1.2.3)
- **Frontend**: Platform-specific (android-2.1.0, ios-2.0.5)
- **Development**: Date-based (20240115-abc123)

### Dependency Management

```python
# Good: Specify minimum compatible version
VersionDependency(
    service_type=ServiceType.BACKEND,
    min_version="1.2.0",
    reason="Requires user authentication API"
)

# Better: Specify version range
VersionDependency(
    service_type=ServiceType.BACKEND,
    min_version="1.2.0",
    max_version="1.3.0",
    reason="Compatible with authentication API v1.2+"
)
```

### Testing Strategy

1. **Unit tests** for version logic
2. **Integration tests** for API contracts
3. **Compatibility tests** in CI/CD
4. **End-to-end tests** across service boundaries

### Documentation

Keep your API documentation updated:

```python
# Good: Documented endpoint with version info
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int) -> UserResponse:
    """
    Get user by ID.
    
    Added in: v1.0.0
    Modified in: v1.2.0 (added created_at field)
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        User information with profile data
        
    Raises:
        404: User not found
        403: Access denied
    """
    return await user_service.get_user(user_id)
```

## 📞 Getting Help

### Common Commands

```bash
# Get help for any command
python cli/version_cli.py --help
python cli/version_cli.py register --help

# Check system status
python cli/version_cli.py list
python cli/version_cli.py deployments

# Emergency compatibility check
python scripts/compatibility_checker.py \
  --service backend \
  --version latest \
  --environment production \
  --fail-on-warnings
```

### Support Channels

1. **Documentation**: Check the [API Reference](api-reference.md)
2. **Troubleshooting**: See [Troubleshooting Guide](troubleshooting.md)
3. **Team Chat**: #version-management Slack channel
4. **Issues**: Create GitHub issue with `version-management` label

---

With this guide, you should be able to effectively use the version management system in your daily development workflow. For more advanced scenarios, refer to the [API Reference](api-reference.md) and [CLI Reference](cli-reference.md).