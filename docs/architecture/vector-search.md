# Vector Search Architecture & Guardrails

## Overview

This document describes the vector search architecture with environment-aware guardrails, provider selection logic, and safety mechanisms to prevent data loss and configuration drift across development, staging, and production environments.

## Provider Selection by Environment

### Default Mapping

| Environment | Default Provider | Override Variable | Fallback Behavior |
|-------------|-----------------|-------------------|-------------------|
| `development` | `local` | `VEC_PROVIDER=pinecone` | Always fallback to local if Pinecone fails |
| `staging` | `local` | Uses `pinecone` if keys present | Fallback to local with WARN |
| `preprod` | `pinecone` | Required | Fallback to local with ERROR |
| `production` | `pinecone` | Required | Fallback to local with ERROR |

### Selection Logic

```python
def select_vector_provider(env: Environment) -> str:
    """Select vector provider based on environment and configuration"""
    
    # Explicit override takes precedence
    explicit_provider = os.getenv("VEC_PROVIDER")
    if explicit_provider in ["local", "pinecone"]:
        return explicit_provider
    
    # Environment-based defaults
    match env:
        case Environment.DEVELOPMENT:
            return "local"  # Safe default for dev
        case Environment.STAGING:
            # Use pinecone if configured, otherwise local
            return "pinecone" if has_pinecone_config() else "local"
        case Environment.PRODUCTION | Environment.PREPROD:
            return "pinecone"  # Required for prod environments
        case _:
            return "local"  # Safe fallback
```

## Configuration Variables

### Core Vector Search Variables

| Variable | Purpose | Required Environments | Default |
|----------|---------|----------------------|---------|
| `VEC_PROVIDER` | Override provider selection | Optional | Environment-based |
| `PINECONE_API_KEY` | Pinecone authentication | staging, preprod, prod | - |
| `PINECONE_ENVIRONMENT` | Pinecone region/environment | staging, preprod, prod | `serverless` |
| `PINECONE_INDEX` | Index name | staging, preprod, prod | Computed |
| `PINECONE_NAMESPACE_PREFIX` | Namespace prefix | Optional | `env=` |
| `VECTOR_STRICT_EMBEDDER_MATCH` | Dimension validation | Optional | `true` |

### Embedding Model Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `EMBEDDING_MODEL` | Model identifier | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Vector dimensions | `384` |

## Index & Namespace Policy

### Index Naming Convention

```
Pattern: pratikoai-embed-{dimension}
Examples:
- pratikoai-embed-384    (for 384-dim embeddings)
- pratikoai-embed-768    (for 768-dim embeddings)
```

### Namespace Structure

All vectors must include these metadata tags:

```python
namespace_components = {
    "env": "dev|staging|preprod|prod",
    "domain": "ccnl|fiscale|legale|lavoro", 
    "tenant": "default"
}

# Full namespace example: "env=dev,domain=fiscale,tenant=default"
```

### Current Production Mapping

| Environment | Index Name | Namespace Prefix | Region |
|-------------|------------|------------------|---------|
| development | `pratikoai-embed-384` | `env=dev` | `serverless` |
| staging | `pratikoai-embed-384` | `env=staging` | `serverless` |
| preprod | `pratikoai-embed-384` | `env=preprod` | `serverless` |
| production | `pratikoai-embed-384` | `env=prod` | `serverless` |

## Safety Mechanisms

### 1. Provider Fallback Logic

```python
class VectorProviderFactory:
    def get_provider(self, env: Environment) -> VectorProvider:
        """Get vector provider with fallback logic"""
        
        selected_provider = self.select_provider(env)
        
        if selected_provider == "pinecone":
            try:
                return PineconeProvider(self.config)
            except Exception as e:
                logger.error("pinecone_initialization_failed", error=str(e))
                
                # Determine fallback behavior based on environment
                if env in [Environment.PRODUCTION, Environment.PREPROD]:
                    logger.error("pinecone_required_for_production")
                    if self.config.VECTOR_STRICT_MODE:
                        raise RuntimeError("Pinecone required for production")
                
                logger.warning("falling_back_to_local_provider")
                return LocalVectorProvider()
        
        return LocalVectorProvider()
```

### 2. Embedder Dimension Validation

```python
def validate_embedder_compatibility(provider, embedding_model):
    """Validate embedder dimensions match index configuration"""
    
    model_dimension = embedding_model.get_sentence_embedding_dimension()
    
    if hasattr(provider, 'get_index_dimension'):
        index_dimension = provider.get_index_dimension()
        
        if model_dimension != index_dimension:
            error_msg = f"Dimension mismatch: model={model_dimension}, index={index_dimension}"
            
            if settings.VECTOR_STRICT_EMBEDDER_MATCH:
                logger.error("embedder_dimension_mismatch_strict", 
                           model_dim=model_dimension, 
                           index_dim=index_dimension)
                raise ValueError(f"{error_msg}. Reindex required.")
            else:
                logger.warning("embedder_dimension_mismatch_permissive",
                             model_dim=model_dimension,
                             index_dim=index_dimension)
```

### 3. Startup Health Checks

```python
def perform_startup_checks():
    """Comprehensive startup validation"""
    
    env = get_environment()
    provider = vector_provider_factory.get_provider(env)
    
    # Log configuration
    logger.info("vector_search_startup",
               provider=provider.name,
               environment=env.value,
               index_name=provider.index_name,
               namespace_prefix=provider.namespace_prefix,
               embedding_model=settings.EMBEDDING_MODEL,
               embedding_dimension=settings.EMBEDDING_DIMENSION)
    
    # Validate embedder compatibility
    validate_embedder_compatibility(provider, embedding_model)
    
    # Test connection
    if hasattr(provider, 'test_connection'):
        try:
            provider.test_connection()
            logger.info("vector_provider_connection_ok")
        except Exception as e:
            logger.warning("vector_provider_connection_failed", error=str(e))
```

## Metrics & Observability

### Metrics to Track

```python
# Provider selection metrics
vector_provider_active = Gauge("vector_provider_active", 
                              "Currently active vector provider", 
                              ["provider"])

# Operation metrics
vector_queries_total = Counter("vector_queries_total",
                              "Total vector queries",
                              ["provider", "status"])

vector_upserts_total = Counter("vector_upserts_total", 
                              "Total vector upserts",
                              ["provider", "status"])

# Error metrics
pinecone_api_errors_total = Counter("pinecone_api_errors_total",
                                   "Total Pinecone API errors",
                                   ["error_type"])

pinecone_unavailable = Event("pinecone_unavailable",
                           "Pinecone service unavailable events")
```

### Startup Logging Template

```
INFO  | vector_search_startup | provider=pinecone environment=development index=pratikoai-embed-384 namespace_prefix=env=dev model=sentence-transformers/all-MiniLM-L6-v2 dimension=384
INFO  | embedder_compatibility_check | model_dim=384 index_dim=384 status=OK
INFO  | vector_provider_connection | status=OK latency_ms=45
INFO  | fallback_configuration | enabled=true strict_mode=false
```

## Migration Strategy

### Preserving Existing Data

1. **No Destructive Operations**: Never delete existing indexes or namespaces
2. **Additive Changes**: Only add new namespaces, don't modify existing ones
3. **Backward Compatibility**: Maintain compatibility with existing `pratikoai-dev` index

### Transition Plan

1. **Phase 1**: Add guardrails without changing current behavior
2. **Phase 2**: Implement namespace prefixes for new data
3. **Phase 3**: Gradually migrate existing data to new namespace structure
4. **Phase 4**: Enforce strict namespace policies

## Error Handling Scenarios

| Scenario | Development | Staging | Production | Action |
|----------|------------|---------|------------|--------|
| Pinecone API key missing | Use local | WARN + local | ERROR + local* | Continue with fallback |
| Pinecone API error | Use local | WARN + local | ERROR + local* | Continue with fallback |
| Dimension mismatch | WARN | WARN | ERROR** | Configurable (strict/permissive) |
| Network timeout | Use local | WARN + local | ERROR + local* | Continue with fallback |

\* Production fallback only if `VECTOR_STRICT_MODE=false`  
\** Production dimension mismatch aborts startup if `VECTOR_STRICT_EMBEDDER_MATCH=true`

## Security Considerations

1. **API Key Management**: Never commit API keys to repository
2. **Environment Isolation**: Each environment uses separate indexes/namespaces
3. **Network Security**: Use TLS for all Pinecone connections
4. **Access Control**: Implement proper IAM for production Pinecone resources
5. **Audit Logging**: Log all vector operations for compliance

## Testing Strategy

1. **Unit Tests**: Mock Pinecone client, test provider selection logic
2. **Integration Tests**: Test against real Pinecone (development only)
3. **Contract Tests**: Verify adapter contracts across providers
4. **Performance Tests**: Validate query latency under load
5. **Chaos Tests**: Simulate Pinecone outages, network failures

---

*This architecture ensures robust, environment-aware vector search with graceful degradation and comprehensive safety mechanisms.*