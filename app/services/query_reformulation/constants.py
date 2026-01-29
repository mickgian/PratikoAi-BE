"""Constants for query reformulation service."""

# Routes that should skip multi-query expansion
# NOTE: theoretical_definition was removed (ADR-022) because queries like
# "Parlami della rottamazione quinquies" need document_references extraction
SKIP_EXPANSION_ROUTES = {"chitchat"}

# DEV-245: Threshold for short query reformulation
# Queries with fewer words than this will be reformulated using LLM
SHORT_QUERY_THRESHOLD = 5
