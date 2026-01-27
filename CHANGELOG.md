# Changelog

All notable changes to the Tangerine ETL project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **WCAG AA Accessibility Testing**: Automated contrast ratio verification for UI colors
  - New accessibility utilities module (`tests/utils/accessibility.py`) implementing WCAG 2.1 standards
  - Comprehensive unit test suite (24 tests) verifying all color combinations meet accessibility standards
  - Dark mode navigation headers: 16.4:1 contrast (WCAG AAA compliant)
  - Dark mode navigation links: 13.4:1 contrast (WCAG AAA compliant)
  - Dark mode tangerine accent: 8.2:1 contrast (WCAG AA compliant)
  - Light mode navigation elements: All meet WCAG AA/AAA standards
  - Tests run on every commit to prevent accessibility regressions
  - Documentation of color usage recommendations for WCAG compliance
- Skills and hooks auto-activation system for Claude Code
- Dev docs system for preserving context across sessions
- Feature documentation workflow with `/doc-feature` command
- **Holiday Management**: New UI in Reference Data page for managing holidays used in business day calculations
  - View all holidays in sortable table
  - Add individual holidays via calendar picker
  - Bulk upload holidays from CSV
  - Edit/delete existing holidays
  - Download holiday list as CSV
  - Statistics showing total, upcoming, and past holidays
- **Dataset Management**: New UI in Monitoring page for full CRUD operations on datasets
  - Create datasets manually with datasource, type, date, and status
  - Edit existing dataset metadata (label, date, source, type, status)
  - Archive datasets (soft delete to Inactive status)
  - Delete datasets with dependency checking (blocks if referenced by regression tests)
  - View all data statuses (Active, Inactive, Deleted, New, Failed, Empty)
- **Log Purge**: New functionality in Monitoring page to delete old logs and prevent database growth
  - Preview how many logs would be deleted before purging
  - View log statistics (total logs, runs, last 7/30 days)
  - Export logs to CSV before deletion (archive)
  - Delete logs older than specified days with confirmation
  - Prevents unbounded growth of tlogentry table
- **Navigation Improvements**: Enhanced user flow and dependency management
  - Import page now checks for required reference data (datasources, dataset types) before allowing configuration creation
  - Warning message with direct link to Reference Data page when dependencies missing
  - Scheduler page offers immediate crontab regeneration after creating a schedule
  - Inbox Rules page now has inline pattern testing directly in Create/Edit forms
  - Real-time pattern validation with match results shown immediately
- **Visual Design Enhancements**: Modern gradient system and sophisticated animations
  - Mesh gradients for hero sections with ambient overlays
  - Animated gradient backgrounds on primary buttons (gradient-shift animation)
  - Button shimmer effects on hover
  - Metric cards with gradient border animation on hover
  - Table headers with animated gradient flow
  - Staggered card entrance animations (fadeInUp)
  - Fixed download button to use Tangerine theme (was green, now orange gradient)
  - Enhanced dark mode with ambient lighting effect at page top
  - More vibrant dark mode alerts with gradient backgrounds and shadows
  - Improved visual depth with layered gradients and sophisticated micro-interactions
- **Custom Typography**: Professional font system with Outfit and JetBrains Mono
  - Outfit font family (weights: 400, 600, 700, 800) for display and body text
  - JetBrains Mono for code blocks and monospace elements
  - Improved letter spacing and font weights for better readability
  - Enhanced typographic hierarchy with distinctive modern appearance
  - Better code readability with dedicated monospace font
  - Consistent typography across all components (headers, labels, tabs, buttons, metrics)
- **Advanced Micro-Interactions**: Sophisticated animations for enhanced user engagement
  - Button click ripple effect with scale pulse
  - Enhanced table row hover with lift and shadow
  - Tab transitions with scale and lift effects
  - Expander content fade-in animation
  - Alert/notification entrance animations (fadeInUp)
  - Progress bar gradient with smooth transitions
  - Loading spinner pulse animation
  - Checkbox/radio hover effects with glow
  - Tab panel content fade-in on switch
  - All animations use cubic-bezier easing for natural movement
- **Recent Items Tracking**: Sidebar widget showing recently viewed/edited items
  - Tracks last 10 items across all pages (shows 5 in sidebar)
  - Displays item type, name, and time ago (e.g., "5m ago", "2h ago")
  - Clear recent items button
  - Automatically removes duplicates
  - Expandable sidebar section for clean interface
- **Auto Dark Mode Detection**: CSS media query respects OS theme preference (`prefers-color-scheme: dark`)
- **Form UX Improvements**: 54 helpful tooltips across admin interface for complex fields

### Changed
- Updated CLAUDE.md with skills, hooks, and documentation sections
- **Inbox Rules UX**: Added inline pattern examples, improved help text, and Quick Start guide for non-technical users
- **Imports UX**: Added file pattern and date format examples with Quick Start guide
- **Scheduler UX**: Added cron expression examples and Quick Start guide for common schedules
- **Reports UX**: Added SQL template syntax and recipient format examples with Quick Start guide
- **Admin Theme**: Improved inline code readability in both light and dark modes

---

## [1.0.0] - 2026-01-16

### Added

#### Infrastructure
- Docker containerization with db, tangerine, admin, and pubsub services
- PostgreSQL 18 database with `dba` and `feeds` schemas
- Connection pooling and transaction management
- Streamlit admin interface at port 8501

#### ETL Framework
- **Generic Import System**: Config-driven file imports supporting CSV, XLS, XLSX, JSON, XML
- **Import Strategies**: Auto-add columns, ignore extras, strict validation
- **Metadata Extraction**: From filename, file content, or static values
- **Date Parsing**: Configurable Java-style date formats
- **File Archiving**: Automatic post-import file movement
- **Dataset Tracking**: Every import creates a dataset record with run_uuid

#### Admin Interface
- **Import Configs**: Full CRUD for import job configurations
- **Reference Data**: Manage datasources and dataset types
- **Run Jobs**: Execute imports with real-time output streaming
- **Monitoring**: View logs, datasets, and statistics with charts
- **Inbox Configs**: Gmail inbox processing rule management
- **Report Manager**: SQL-based email report configuration
- **Scheduler**: Database-driven cron job management
- **Event System**: Pub/sub event queue and subscriber management

#### Email Services
- **Gmail Integration**: OAuth2-based Gmail API client
- **Inbox Processor**: Download email attachments based on pattern rules
- **Report Generator**: SQL query results as HTML emails with attachments

#### Pub/Sub System
- Event queue with database-backed persistence
- File watcher for event triggers
- Subscriber notification system
- ETL integration (import_complete, report_sent, email_received events)

#### Testing
- 310+ pytest-based tests for admin interface
- 121 ETL integration tests
- 17 ETL regression tests
- Transaction-based test isolation

#### Developer Experience
- Custom CSS theme (Tangerine orange)
- Codemaps for architecture documentation
- Slash commands for common operations
- Code style guide with ruff linting

### Database Tables

#### Configuration
- `dba.timportconfig` - Import job configurations
- `dba.tdatasource` - Data source reference
- `dba.tdatasettype` - Dataset type reference
- `dba.timportstrategy` - Import strategies

#### Email Services
- `dba.tinboxconfig` - Gmail inbox processing rules
- `dba.treportmanager` - Report configurations
- `dba.tscheduler` - Cron job definitions

#### Pub/Sub
- `dba.tpubsub_events` - Event queue
- `dba.tpubsub_subscribers` - Event subscribers

#### Tracking
- `dba.tdataset` - Dataset metadata
- `dba.tlogentry` - ETL execution logs

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-01-16 | Initial release with full ETL pipeline |

---

## How to Update This File

When making changes:

1. Add entries under `[Unreleased]` section
2. Use these categories:
   - **Added** - New features
   - **Changed** - Changes to existing functionality
   - **Deprecated** - Features to be removed
   - **Removed** - Removed features
   - **Fixed** - Bug fixes
   - **Security** - Security fixes

3. Format entries as:
   ```markdown
   - **Feature Name**: Brief description of the change
   ```

4. When releasing, move `[Unreleased]` items to a new version section
