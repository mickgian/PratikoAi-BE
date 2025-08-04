-- Migration: Create vector metadata tables
-- Description: Creates tables to store vector database metadata and search history
-- Created: 2024-01-01

-- Create vector_documents table to track indexed documents
CREATE TABLE IF NOT EXISTS vector_documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    content_preview TEXT,
    document_type VARCHAR(100) NOT NULL,
    language VARCHAR(50) DEFAULT 'italian',
    metadata JSONB DEFAULT '{}',
    text_hash VARCHAR(32),
    text_length INTEGER,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    
    -- Indexes for efficient querying
    INDEX idx_vector_documents_document_id (document_id),
    INDEX idx_vector_documents_type (document_type),
    INDEX idx_vector_documents_language (language),
    INDEX idx_vector_documents_indexed_at (indexed_at),
    INDEX idx_vector_documents_user_id (user_id)
);

-- Create vector_search_history table to track search queries
CREATE TABLE IF NOT EXISTS vector_search_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    search_query TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- 'semantic', 'hybrid', 'keyword'
    knowledge_type VARCHAR(100), -- 'regulation', 'tax_rate', 'template', etc.
    language VARCHAR(50) DEFAULT 'italian',
    results_count INTEGER DEFAULT 0,
    semantic_weight FLOAT,
    filters JSONB DEFAULT '{}',
    search_results JSONB DEFAULT '[]',
    search_duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for analytics and performance
    INDEX idx_vector_search_session (session_id),
    INDEX idx_vector_search_user (user_id),
    INDEX idx_vector_search_type (search_type),
    INDEX idx_vector_search_knowledge_type (knowledge_type),
    INDEX idx_vector_search_created_at (created_at)
);

-- Create vector_index_stats table to track index health and usage
CREATE TABLE IF NOT EXISTS vector_index_stats (
    id SERIAL PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    total_vector_count INTEGER DEFAULT 0,
    dimension INTEGER DEFAULT 384,
    index_fullness FLOAT DEFAULT 0.0,
    storage_usage_mb FLOAT DEFAULT 0.0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    
    -- Unique constraint on index name and date (for daily snapshots)
    UNIQUE(index_name, DATE(last_updated))
);

-- Create vector_document_relations table to track relationships between documents
CREATE TABLE IF NOT EXISTS vector_document_relations (
    id SERIAL PRIMARY KEY,
    source_document_id VARCHAR(255) NOT NULL,
    related_document_id VARCHAR(255) NOT NULL,
    relation_type VARCHAR(100) NOT NULL, -- 'similar', 'references', 'supersedes', etc.
    similarity_score FLOAT,
    relation_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    FOREIGN KEY (source_document_id) REFERENCES vector_documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (related_document_id) REFERENCES vector_documents(document_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_vector_relations_source (source_document_id),
    INDEX idx_vector_relations_related (related_document_id),
    INDEX idx_vector_relations_type (relation_type),
    INDEX idx_vector_relations_score (similarity_score)
);

-- Create vector_sync_status table to track synchronization with external systems
CREATE TABLE IF NOT EXISTS vector_sync_status (
    id SERIAL PRIMARY KEY,
    source_system VARCHAR(100) NOT NULL, -- 'italian_regulations', 'tax_rates', 'templates'
    source_table VARCHAR(100) NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
    documents_synced INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    error_details TEXT,
    sync_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint on source system and table
    UNIQUE(source_system, source_table),
    
    -- Indexes
    INDEX idx_vector_sync_status (sync_status),
    INDEX idx_vector_sync_last_sync (last_sync_at)
);

-- Add comments for documentation
COMMENT ON TABLE vector_documents IS 'Tracks documents indexed in the vector database';
COMMENT ON TABLE vector_search_history IS 'Logs all vector search queries for analytics and debugging';
COMMENT ON TABLE vector_index_stats IS 'Stores periodic snapshots of vector index statistics';
COMMENT ON TABLE vector_document_relations IS 'Tracks relationships and similarities between documents';
COMMENT ON TABLE vector_sync_status IS 'Monitors synchronization status with external data sources';

-- Insert initial sync status records for Italian knowledge sources
INSERT INTO vector_sync_status (source_system, source_table, sync_status) VALUES
    ('italian_knowledge', 'italian_regulations', 'pending'),
    ('italian_knowledge', 'italian_tax_rates', 'pending'),
    ('italian_knowledge', 'italian_legal_templates', 'pending')
ON CONFLICT (source_system, source_table) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_vector_documents_updated_at 
    BEFORE UPDATE ON vector_documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vector_sync_status_updated_at 
    BEFORE UPDATE ON vector_sync_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions (adjust as needed for your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;