-- Local development role separation (NX-022).
--
-- The service must not connect as a superuser or as the owner of its tables:
-- both bypass the ACL that makes audit_record append-only, so the control would
-- express itself correctly in pg_class.relacl and enforce nothing.
--
-- nexus      - owns the schema, runs migrations (superuser here only because
--              the postgres image makes POSTGRES_USER one)
-- nexus_app  - what the service connects as; no superuser, owns nothing
--
-- Development credentials only. Deployed environments take both roles and their
-- secrets from the secret manager (SDD 10.2).

CREATE ROLE nexus_app WITH LOGIN PASSWORD 'nexus_app' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE nexus TO nexus_app;
GRANT USAGE ON SCHEMA public TO nexus_app;
