# OpenCode UI/UX Specifications for Tangerine ETL Admin Interface

## Overview

This specification document outlines a comprehensive UI/UX redesign for the Tangerine ETL admin interface. The goal is to transform the current CRUD-heavy, entity-focused interface into an intuitive, task-driven system that guides users through ETL workflows while maintaining all existing functionality.

### Current State Analysis
- **Structure**: 8 separate pages organized by data entities (Imports, Reference Data, etc.)
- **Navigation**: Flat list with no guided flow
- **Dependencies**: Not enforced or visualized
- **User Experience**: Requires domain knowledge to understand correct sequences
- **Job Management**: Fragmented across multiple pages

### Target State Goals
- **Intuitive Navigation**: Task-based organization with guided workflows
- **Dependency Awareness**: Automatic prerequisite checking and creation guidance
- **Progressive Complexity**: Scale from simple to advanced based on user needs
- **Unified Job Hub**: Single interface for all job-related operations
- **Guided Onboarding**: Step-by-step wizards for new users

## Proposed Architecture

### Navigation Structure

```python
# Main navigation hierarchy
navigation = {
    "🏠 Dashboard": [
        {"🚀 Getting Started": "pages/getting_started.py"},
        {"📊 Overview": "pages/dashboard.py"}
    ],
    "⚙️ Setup": [
        {"📊 Data Sources & Types": "pages/setup_data.py"},
        {"📁 Import Configurations": "pages/setup_imports.py"},
        {"📧 Inbox Rules": "pages/setup_inbox.py"}
    ],
    "🎯 Jobs": [
        {"📋 Job Hub": "pages/jobs_hub.py"},
        {"➕ Create Job": "pages/jobs_create.py"},
        {"📅 Scheduled Jobs": "pages/jobs_scheduled.py"}
    ],
    "📊 Monitoring": [
        {"📈 Analytics": "pages/monitoring_analytics.py"},
        {"📋 Logs & Data": "pages/monitoring_logs.py"}
    ],
    "🤖 Automation": [
        {"📧 Reports": "pages/automation_reports.py"},
        {"⏰ Scheduler": "pages/automation_scheduler.py"},
        {"📡 Events": "pages/automation_events.py"}
    ]
}
```

### Component Architecture

```python
# Shared components to implement
components = {
    "wizard.py": "Multi-step guided workflows",
    "dependency_checker.py": "Prerequisite validation and guidance",
    "job_card.py": "Unified job display component",
    "action_bar.py": "Contextual action buttons",
    "status_badge.py": "Color-coded status indicators",
    "progress_indicator.py": "Step progress visualization"
}
```

## User Flows & Design Patterns

### 1. New User Onboarding Flow

**Flow Sequence**:
1. Dashboard → Getting Started wizard
2. Step 1: Data Source setup (with examples)
3. Step 2: Dataset Type selection
4. Step 3: Import Configuration (file patterns, mappings)
5. Step 4: Test run with sample data
6. Step 5: Schedule or save for manual execution

**Implementation Pattern**:
```python
class OnboardingWizard:
    def __init__(self):
        self.steps = [
            {"title": "Data Source", "component": DataSourceStep},
            {"title": "Dataset Type", "component": DatasetTypeStep},
            {"title": "Import Config", "component": ImportConfigStep},
            {"title": "Test Run", "component": TestRunStep},
            {"title": "Schedule", "component": ScheduleStep}
        ]
        self.current_step = 0
        self.data = {}

    def render(self):
        # Progress indicator
        self.render_progress()

        # Current step content
        step = self.steps[self.current_step]
        step["component"](self.data).render()

        # Navigation buttons
        self.render_navigation()
```

### 2. Dependency-Guided Creation

**Pattern**: Before allowing creation, check prerequisites and offer guided setup.

```python
class DependencyChecker:
    @staticmethod
    def check_import_config_prerequisites():
        """Check if user can create import configs"""
        sources = get_data_sources()
        types = get_dataset_types()

        missing = []
        if not sources:
            missing.append({"type": "data_source", "action": "create_data_source"})
        if not types:
            missing.append({"type": "dataset_type", "action": "create_dataset_type"})

        return missing

    @staticmethod
    def render_guidance(missing_deps):
        """Show guidance UI for missing dependencies"""
        if missing_deps:
            st.warning("Some prerequisites are missing:")
            for dep in missing_deps:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {dep['type'].replace('_', ' ').title()}")
                with col2:
                    if st.button(f"Create {dep['type'].replace('_', ' ')}",
                               key=f"create_{dep['type']}"):
                        st.session_state[f"create_{dep['type']}"] = True
                        st.rerun()
```

### 3. Unified Job Hub

**Core Component**: Single table view with filtering and actions.

```python
class JobHub:
    def __init__(self):
        self.jobs = self.load_all_jobs()
        self.filters = {
            "status": ["all", "running", "completed", "failed", "scheduled"],
            "type": ["all", "manual", "scheduled", "event"],
            "date_range": "last_7_days"
        }

    def render(self):
        # Filters bar
        self.render_filters()

        # Jobs table
        self.render_jobs_table()

        # Bulk actions
        self.render_bulk_actions()

    def render_jobs_table(self):
        # Use Streamlit dataframe with custom column config
        df = pd.DataFrame(self.jobs)
        st.dataframe(
            df,
            column_config={
                "name": st.column_config.TextColumn("Job Name", width="large"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "last_run": st.column_config.DatetimeColumn("Last Run", format="YYYY-MM-DD HH:mm"),
                "next_run": st.column_config.DatetimeColumn("Next Run", format="YYYY-MM-DD HH:mm"),
                "actions": st.column_config.TextColumn("Actions", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
```

## Page-by-Page Implementation Specs

### 1. Dashboard (`pages/dashboard.py`)

**Current**: Static metrics
**New**: Action-oriented landing page

```python
def render_dashboard():
    # Header with quick actions
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("🏠 Tangerine ETL Dashboard")
    with col2:
        if st.button("🚀 Getting Started", type="primary"):
            st.session_state.show_onboarding = True
    with col3:
        if st.button("➕ Quick Job", type="secondary"):
            st.switch_page("pages/jobs_create.py")

    # Quick action cards
    render_action_cards()

    # Recent activity
    render_recent_activity()

    # System health
    render_system_health()

def render_action_cards():
    cards = [
        {"title": "Create Job", "icon": "➕", "desc": "Set up new ETL job", "page": "jobs_create"},
        {"title": "Run Import", "icon": "▶️", "desc": "Execute existing job", "page": "jobs_hub"},
        {"title": "View Data", "icon": "📊", "desc": "Browse loaded datasets", "page": "monitoring_logs"},
        {"title": "Configure", "icon": "⚙️", "desc": "Set up data sources", "page": "setup_data"}
    ]

    cols = st.columns(4)
    for i, card in enumerate(cards):
        with cols[i]:
            with st.container(border=True):
                st.subheader(f"{card['icon']} {card['title']}")
                st.caption(card['desc'])
                if st.button("Go", key=f"card_{i}"):
                    st.switch_page(f"pages/{card['page']}.py")
```

### 2. Getting Started Wizard (`pages/getting_started.py`)

**Purpose**: Guided onboarding for new users

```python
def render_getting_started():
    st.title("🚀 Getting Started with Tangerine ETL")

    wizard = OnboardingWizard()
    wizard.render()

    # Skip option for advanced users
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Skip to Advanced Interface", type="secondary"):
            st.session_state.onboarding_complete = True
            st.session_state.preferred_mode = "advanced"
            st.rerun()
```

### 3. Setup Data Page (`pages/setup_data.py`)

**Purpose**: Unified management of data sources, types, and strategies

```python
def render_setup_data():
    st.title("⚙️ Data Sources & Types")

    tab_sources, tab_types, tab_strategies = st.tabs([
        "📊 Data Sources", "🏷️ Dataset Types", "🔧 Import Strategies"
    ])

    with tab_sources:
        render_data_sources_tab()

    with tab_types:
        render_dataset_types_tab()

    with tab_strategies:
        render_import_strategies_tab()  # Read-only

def render_data_sources_tab():
    # Check if any sources exist
    sources = get_data_sources()
    if not sources:
        render_empty_state(
            "No data sources configured",
            "Data sources define where your data comes from (files, APIs, databases, etc.)",
            "Create your first data source to get started"
        )

    # List existing sources
    for source in sources:
        with st.expander(f"**{source['name']}**", expanded=len(sources) == 1):
            render_source_details(source)

    # Create new source
    with st.expander("➕ Add New Data Source", expanded=not sources):
        render_create_source_form()
```

### 4. Jobs Hub (`pages/jobs_hub.py`)

**Purpose**: Unified job management interface

```python
def render_jobs_hub():
    st.title("🎯 Job Hub")

    # Quick stats
    render_job_stats()

    # Main interface with tabs
    tab_all, tab_running, tab_scheduled = st.tabs([
        "📋 All Jobs", "⚡ Running", "📅 Scheduled"
    ])

    with tab_all:
        hub = JobHub()
        hub.render()

    with tab_running:
        render_running_jobs()

    with tab_scheduled:
        render_scheduled_jobs()
```

## Component Specifications

### Wizard Component (`components/wizard.py`)

```python
class Step:
    def __init__(self, title, component_class, data_key=None):
        self.title = title
        self.component_class = component_class
        self.data_key = data_key

    def render(self, wizard_data):
        return self.component_class(wizard_data).render()

class Wizard:
    def __init__(self, steps, on_complete=None):
        self.steps = steps
        self.current_step = 0
        self.data = {}
        self.on_complete = on_complete

    def render_progress(self):
        # Visual progress indicator
        progress = (self.current_step + 1) / len(self.steps)
        st.progress(progress)

        # Step indicators
        cols = st.columns(len(self.steps))
        for i, step in enumerate(self.steps):
            with cols[i]:
                if i < self.current_step:
                    st.success(f"✓ {step.title}")
                elif i == self.current_step:
                    st.info(f"➤ {step.title}")
                else:
                    st.caption(step.title)

    def render_navigation(self):
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if self.current_step > 0:
                if st.button("⬅️ Back", key="wizard_back"):
                    self.current_step -= 1
                    st.rerun()

        with col2:
            st.write(f"Step {self.current_step + 1} of {len(self.steps)}")

        with col3:
            if self.current_step < len(self.steps) - 1:
                if st.button("Next ➡️", key="wizard_next", type="primary"):
                    if self.validate_current_step():
                        self.current_step += 1
                        st.rerun()
            else:
                if st.button("Complete ✅", key="wizard_complete", type="primary"):
                    if self.validate_current_step():
                        if self.on_complete:
                            self.on_complete(self.data)
                        st.success("Setup complete!")
                        st.balloons()

    def validate_current_step(self):
        # Implement validation logic
        return True
```

### Dependency Checker (`components/dependency_checker.py`)

```python
class DependencyChecker:
    @staticmethod
    def check_prerequisites(action_type, context_data=None):
        """Check prerequisites for given action"""
        checks = {
            "create_import": DependencyChecker.check_import_prerequisites,
            "create_job": DependencyChecker.check_job_prerequisites,
            "run_import": DependencyChecker.check_run_prerequisites
        }

        if action_type in checks:
            return checks[action_type](context_data)
        return []

    @staticmethod
    def render_dependency_guidance(missing_deps, action_context):
        """Render UI to guide user through missing dependencies"""
        if not missing_deps:
            return True  # All good

        st.warning(f"Before {action_context}, you'll need to set up:")

        for dep in missing_deps:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• **{dep['friendly_name']}**")
                    if 'description' in dep:
                        st.caption(dep['description'])
                with col2:
                    if st.button(f"Set up {dep['friendly_name']}",
                               key=f"setup_{dep['type']}"):
                        # Navigate to appropriate setup page
                        st.session_state[f"setup_{dep['type']}"] = True
                        st.rerun()

        return False  # Block action until dependencies are met
```

## Session State Management

```python
# Initialize session state
def init_session_state():
    defaults = {
        "onboarding_complete": False,
        "preferred_mode": "simple",  # simple or advanced
        "last_action_context": None,
        "show_onboarding": False,
        "current_wizard_step": 0,
        "wizard_data": {}
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Call at the start of each page
init_session_state()
```

## Implementation Priority

### Phase 1: Foundation
1. Create new navigation structure
2. Implement wizard component
3. Build dependency checker
4. Create dashboard with action cards

### Phase 2: Core Pages
1. Jobs Hub (unified job management)
2. Setup Data (unified reference data)
3. Getting Started wizard

### Phase 3: Enhancement
1. Progressive disclosure features
2. Advanced mode toggles
3. Bulk operations
4. Predictive features

## Testing Strategy

### User Flow Testing
- End-to-end walkthroughs of key workflows
- A/B testing of simple vs advanced modes
- Usability testing with sample users

### Component Testing
- Unit tests for wizard navigation
- Integration tests for dependency checking
- Performance tests for large job lists

## Migration Plan

### Gradual Rollout
1. Add new pages alongside existing ones
2. Update navigation to include new structure
3. Mark old pages as "Legacy" with migration guides
4. Eventually deprecate old pages

### Backward Compatibility
- Existing direct links continue to work
- User preferences (advanced/simple mode) persist
- Data migrations handled by existing services

This specification provides a complete blueprint for transforming the Tangerine admin interface into an intuitive, user-friendly ETL management system. The modular component architecture ensures maintainability while the task-focused design dramatically improves user experience.</content>
<parameter name="filePath">/opt/tangerine/opencode_specs.md