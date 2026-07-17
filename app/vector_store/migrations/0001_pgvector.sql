CREATE EXTENSION IF NOT EXISTS vector;

-- SQLAlchemy owns the complete table shape. This module-owned migration documents
-- the PostgreSQL prerequisite without modifying Owner 1's Alembic chain.
CREATE INDEX IF NOT EXISTS ix_document_embeddings_vector_cosine
ON document_embeddings USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);
