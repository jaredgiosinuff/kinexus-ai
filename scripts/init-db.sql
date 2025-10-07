-- Initialize database for Kinexus AI development
-- This script runs automatically when PostgreSQL container starts

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create extension for vector operations (if using pgvector)
-- Note: This requires pgvector to be installed in the PostgreSQL image
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Create development user with appropriate permissions
DO $$
BEGIN
    -- Check if role exists
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kinexus_dev') THEN
        CREATE ROLE kinexus_dev WITH
            LOGIN
            NOSUPERUSER
            CREATEDB
            NOCREATEROLE
            INHERIT
            NOREPLICATION
            CONNECTION LIMIT -1
            PASSWORD 'kinexus_dev_pass';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE kinexus_dev TO kinexus_dev;
GRANT CREATE ON DATABASE kinexus_dev TO kinexus_dev;

-- Create schema for application
CREATE SCHEMA IF NOT EXISTS kinexus AUTHORIZATION kinexus_user;

-- Grant permissions on schema
GRANT USAGE ON SCHEMA kinexus TO kinexus_dev;
GRANT CREATE ON SCHEMA kinexus TO kinexus_dev;

-- Set default schema for user
ALTER ROLE kinexus_user SET search_path TO kinexus, public;
ALTER ROLE kinexus_dev SET search_path TO kinexus, public;