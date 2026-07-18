# Security Policy

flask-rls enforces data isolation at the database level. Because it is a security-sensitive
library, we take vulnerability reports seriously.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Instead, report them
privately via [GitHub Security Advisories](https://github.com/kdpisda/flask-rls/security/advisories/new)
or by email to pisdak79@gmail.com.

Include:

- a description of the vulnerability and its impact,
- steps to reproduce (a minimal policy + query is ideal),
- affected versions.

We aim to acknowledge reports within 72 hours.

## Scope and expectations

flask-rls sets a per-transaction PostgreSQL session variable (`set_config('rls.*', …, true)`)
so your RLS policies enforce isolation. Correct isolation depends on:

- your application connecting as a **non-owner** database role (table owners bypass RLS
  unless `FORCE ROW LEVEL SECURITY` is set — flask-rls emits `FORCE`, but a superuser role
  bypasses RLS regardless);
- policies covering every access path (`ALL`, or the specific operations you need);
- context being set for every request path that reads tenant data.

Misconfiguration in these areas is a deployment concern, not a library vulnerability, but we
are happy to clarify guidance — open a regular issue for questions.
