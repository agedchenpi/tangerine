# Feature Documentation

This directory contains detailed documentation for each major feature in the Tangerine ETL system.

## Feature Index

| Feature | Description | Added |
|---------|-------------|-------|
| [Generic Import](generic-import.md) | Config-driven file imports (CSV, Excel, JSON, XML) | 2026-01-16 |
| [Gmail Integration](gmail-integration.md) | OAuth2 Gmail client for sending/receiving emails | 2026-01-16 |
| [Inbox Processor](inbox-processor.md) | Download email attachments based on rules | 2026-01-16 |
| [Report Generator](report-generator.md) | SQL-based email reports with attachments | 2026-01-16 |
| [Pub/Sub System](pubsub-system.md) | Event queue and subscriber notifications | 2026-01-16 |
| [Admin Interface](admin-interface.md) | Streamlit-based configuration UI | 2026-01-16 |
| [Skills & Hooks](skills-hooks.md) | Claude Code auto-activation system | 2026-01-16 |

## Documentation Template

When adding a new feature, use the `/doc-feature` command which provides a template including:

- Overview and purpose
- Component architecture
- Data flow
- Usage examples
- Configuration options
- Database tables
- Testing instructions
- Known limitations
- Future improvements

## Quick Links

### By Category

**ETL Jobs:**
- [Generic Import](generic-import.md)
- [Inbox Processor](inbox-processor.md)
- [Report Generator](report-generator.md)

**External Integrations:**
- [Gmail Integration](gmail-integration.md)

**System Features:**
- [Pub/Sub System](pubsub-system.md)
- [Admin Interface](admin-interface.md)

**Developer Tools:**
- [Skills & Hooks](skills-hooks.md)

## Adding New Features

1. Create feature file: `docs/features/{feature-name}.md`
2. Use the template from `/doc-feature` command
3. Add entry to this index table
4. Update `CHANGELOG.md` with the change
