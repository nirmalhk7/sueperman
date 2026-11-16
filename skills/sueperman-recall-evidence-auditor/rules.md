# Existing rule references

- services/api/app/matching/recall.py: authoritative recall hard conditions.
- services/api/app/matching/normalize.py: exact permitted normalization.
- services/api/app/security/source_policy.py: official-source provenance.
- services/api/app/diwali/core.py: manager consumes the independent rule result.

The package manifest pins exact rule bytes at build time. Changed rule bytes
require a new review/pin. Procedures never execute these paths or replace them.
