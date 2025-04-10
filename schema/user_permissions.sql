-- Grant basic DML permissions on the tables
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE data_sources TO your_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE documents TO your_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE document_chunks TO your_app_user;

-- Grant USAGE permission on the sequences used for SERIAL/BIGSERIAL primary keys
-- (Required for INSERT operations to generate IDs automatically)
GRANT USAGE, SELECT ON SEQUENCE data_sources_source_id_seq TO your_app_user;
GRANT USAGE, SELECT ON SEQUENCE documents_document_id_seq TO your_app_user;
-- Assuming the chunk_id sequence name follows the pattern:
GRANT USAGE, SELECT ON SEQUENCE document_chunks_chunk_id_seq TO your_app_user;

-- Optional: Grant permission to use the 'vector' extension's functions if needed directly
-- Usually not required if only using SQLAlchemy's pgvector integration
-- GRANT USAGE ON SCHEMA public TO your_app_user; -- Might be needed depending on setup

-- Optional but Recommended for future tables/sequences created by this user or in this schema:
-- If your tables are in the 'public' schema (the default):
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO your_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO your_app_user;