---
name: streamlit-design
description: Create distinctive, production-grade Streamlit interfaces with exceptional design quality. Use when building admin pages, dashboards, data apps, or components that need to transcend generic UI patterns.
---

# Streamlit Design Guidelines

## 1. Introduction

### When to Use This Skill

Use this skill when:
- Building Streamlit pages, components, dashboards, or data apps
- User explicitly mentions "design", "beautiful", "distinctive", "custom styling"
- User asks to "make it look better" or "improve the UI"
- Creating customer-facing dashboards or reports
- The interface needs to convey a specific brand or aesthetic

### Design Philosophy

**Bold, Distinctive, Context-Appropriate > Generic Patterns**

The goal is to create interfaces that:
- **Tell a story** through intentional visual choices
- **Match their context** (data lab looks different from content app)
- **Transcend defaults** without sacrificing functionality
- **Respect constraints** while pushing creative boundaries

### Streamlit-Specific Considerations

Streamlit is a Python framework for data apps with:
- Server-side rendering (stateful via session_state)
- Component-based architecture (columns, containers, tabs)
- Limited native styling (CSS is your friend)
- Rapid prototyping focus (balance speed with quality)

### Integration with Existing Patterns

This skill provides the **aesthetic layer** on top of structural patterns:
- **Streamlit-Admin**: Provides page structure, forms, services, session state
- **Streamlit-Design**: Provides custom CSS, unique components, visual identity

Always use streamlit-admin patterns for structure, then enhance with design.

---

## 2. Design Thinking Framework

**CRITICAL: Answer these questions BEFORE writing any code.**

### Question 1: Purpose

**What problem does this interface solve?**
- Who are the users? (developers, analysts, executives, customers)
- What data story are you telling?
- What actions do users need to take?
- What's the primary goal? (exploration, monitoring, reporting, editing)

### Question 2: Tone

**Choose an extreme aesthetic direction:**

**DO NOT settle for "neutral" or "generic". Pick a clear direction and execute with precision.**

Options:
- **Industrial/Data-driven** (current Tangerine theme)
  - Orange/metal/slate colors, utilitarian, functional
  - Best for: Admin tools, ETL interfaces, system monitoring

- **Editorial/Magazine** (sophisticated, hierarchical)
  - Serif fonts, generous whitespace, elegant typography
  - Best for: Report viewers, narrative data, content apps

- **Minimal/Zen** (restraint, whitespace, precision)
  - 1-2 colors, geometric shapes, subtle interactions
  - Best for: Focus-driven tools, data exploration, clean dashboards

- **Playful/Whimsical** (fun, unexpected, colorful)
  - Bright colors, rounded shapes, micro-animations
  - Best for: Consumer apps, gamified interfaces, creative tools

- **Brutalist/Raw** (utilitarian, monospace, stark)
  - Black/white/red, borders everywhere, uppercase
  - Best for: Developer tools, logs, system internals

- **Luxury/Refined** (elegant, serif, premium)
  - Gold accents, dark backgrounds, sophisticated palette
  - Best for: Executive dashboards, premium features, high-value data

- **Organic/Natural** (soft, flowing, earth tones)
  - Rounded corners, gradients, warm colors
  - Best for: Health apps, environmental data, human-centered tools

- **Retro/Nostalgic** (80s/90s vibes, neon, geometric)
  - Vibrant colors, bold shapes, nostalgic fonts
  - Best for: Creative tools, data viz experiments, fun projects

- **Art Deco/Geometric** (bold shapes, symmetry, gold accents)
  - Geometric patterns, metallic colors, elegant proportions
  - Best for: Premium dashboards, financial apps, architectural data

### Question 3: Constraints

**What limitations must you work within?**
- Performance requirements (large datasets, real-time updates)
- Accessibility needs (WCAG compliance, screen readers)
- Browser support (modern only or legacy)
- Mobile/responsive requirements
- Development time (quick prototype vs. polished product)

### Question 4: Differentiation

**What's the ONE thing users will remember about this interface?**
- A signature color combination?
- An unexpected animation?
- Elegant typography?
- Creative data visualization?
- Memorable micro-interaction?

**CRITICAL: If you can't answer this question, your design will be forgettable.**

---

## 3. Streamlit Aesthetics Guidelines

### 3.1 Typography

Custom fonts are the fastest way to establish identity.

**Font Loading via CSS:**

```css
/* In styles/custom.css or inline with st.markdown */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
    --font-display: 'Syne', sans-serif;
    --font-body: 'IBM Plex Sans', sans-serif;
}

h1, h2, h3 {
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: -0.02em;
}

.stMarkdown, .stText, p {
    font-family: var(--font-body);
    line-height: 1.6;
}
```

**Font Pairing Strategies:**

| Strategy | Example | Best For |
|----------|---------|----------|
| Display + Body | Syne (display) + IBM Plex (body) | Modern apps |
| Serif + Sans | Playfair Display + Inter | Editorial content |
| Mono + Rounded | JetBrains Mono + DM Sans | Developer tools |
| Geometric + Humanist | Outfit + Source Sans | Clean dashboards |

**Avoid These Fonts:**
- ❌ Default system fonts (Arial, Times New Roman)
- ❌ Overused AI choices (Inter everywhere, Space Grotesk, Roboto)
- ❌ Comic Sans, Papyrus, Brush Script (unless intentionally kitsch)

**Distinctive Font Choices:**
- ✅ **Display**: Syne, Outfit, Archivo, DM Sans, General Sans, Manrope, Epilogue
- ✅ **Body**: IBM Plex Sans, Source Serif Pro, Work Sans, Plus Jakarta Sans
- ✅ **Mono**: JetBrains Mono, Fira Code, IBM Plex Mono, Space Mono

**Streamlit-Specific Typography Selectors:**

```css
/* Headers */
h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }

/* Markdown content */
.stMarkdown p {
    font-size: 1rem;
    line-height: 1.7;
}

/* Buttons */
.stButton > button {
    font-family: var(--font-body);
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
}

/* Text inputs */
.stTextInput > div > div > input {
    font-family: var(--font-body);
}

/* DataFrames */
.stDataFrame {
    font-size: 0.9rem;
}

/* Tab labels */
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
}
```

**Typography Hierarchy:**

```css
/* Clear visual hierarchy */
h1 {
    font-size: 3rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 0.5rem;
}

h2 {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 1rem;
}

h3 {
    font-size: 1.5rem;
    font-weight: 600;
    line-height: 1.3;
}

p, .stMarkdown {
    font-size: 1rem;
    line-height: 1.7;
    color: var(--text-secondary);
}

/* Small text */
.caption, .small-text {
    font-size: 0.875rem;
    color: var(--text-tertiary);
}
```

### 3.2 Color & Theme

**Use CSS Custom Properties:**

```css
:root {
    /* Base palette */
    --color-primary: #FF8C42;
    --color-secondary: #6C63FF;
    --color-accent: #FF6B9D;

    /* Backgrounds */
    --color-bg: #F8F9FA;
    --color-card-bg: #FFFFFF;

    /* Text */
    --color-text: #2C3E50;
    --color-text-secondary: #6C757D;
    --color-text-tertiary: #ADB5BD;

    /* Borders */
    --color-border: #DEE2E6;

    /* Status colors */
    --color-success: #28A745;
    --color-warning: #FFC107;
    --color-error: #DC3545;
    --color-info: #17A2B8;

    /* Gradients */
    --gradient-primary: linear-gradient(135deg, #FF8C42 0%, #FFA45C 100%);
    --gradient-secondary: linear-gradient(135deg, #6C63FF 0%, #8B7FFF 100%);

    /* Shadows */
    --shadow-sm: 0 2px 4px rgba(0,0,0,0.08);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.12);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.16);
    --shadow-xl: 0 16px 48px rgba(0,0,0,0.2);
}

/* Dark mode overrides */
[data-theme="dark"] {
    --color-bg: #1A1A1A;
    --color-card-bg: #2C2C2C;
    --color-text: #E8E8E8;
    --color-text-secondary: #B0B0B0;
    --color-border: #404040;
}
```

**Theme Management (Existing Pattern):**

```python
from admin.utils.ui_helpers import is_dark_mode, get_theme_colors

# Get current theme colors
colors = get_theme_colors()
# Returns dict with: bg, card_bg, text_primary, text_secondary, accent, border, etc.

# Check theme state
if is_dark_mode():
    # Dark mode specific logic
    background = colors['bg']
else:
    # Light mode
    background = colors['bg']

# Use in markdown
st.markdown(f"""
<div style="background-color: {colors['card_bg']}; color: {colors['text_primary']};">
    Themed content
</div>
""", unsafe_allow_html=True)
```

**Color Psychology for Data Apps:**

| Color | Meaning | Best Use Cases |
|-------|---------|----------------|
| Red/Orange | Energy, urgency, warnings | Alerts, CTAs, Tangerine primary |
| Blue | Trust, stability, calm | Data viz, info messages, primary actions |
| Green | Success, growth, positive | Success states, positive metrics, "go" actions |
| Purple | Creativity, luxury, innovation | Premium features, creative tools |
| Yellow | Attention, caution, highlights | Warnings, highlights, important info |
| Gray | Neutral, professional, subtle | Text, borders, backgrounds |
| Black/White | Contrast, clarity, stark | Typography, minimalism, brutalist |

**Color Palette Construction:**

```css
/* 60-30-10 Rule: 60% dominant, 30% secondary, 10% accent */

/* Monochromatic */
:root {
    --color-base: #FF8C42;
    --color-light: #FFB076;
    --color-lighter: #FFD4B0;
    --color-dark: #E57735;
    --color-darker: #CC6028;
}

/* Complementary */
:root {
    --color-primary: #FF8C42; /* Orange */
    --color-complement: #42BAFF; /* Blue */
}

/* Triadic */
:root {
    --color-primary: #FF8C42; /* Orange */
    --color-secondary: #42FF8C; /* Green */
    --color-tertiary: #8C42FF; /* Purple */
}

/* Analogous */
:root {
    --color-primary: #FF8C42; /* Orange */
    --color-secondary: #FFCF42; /* Yellow-orange */
    --color-tertiary: #FF4242; /* Red-orange */
}
```

### 3.3 Layout & Composition

**Creative Column Ratios:**

```python
# Instead of equal columns
col1, col2, col3 = st.columns(3)

# Use interesting ratios
col1, col2, col3 = st.columns([1, 2, 1])  # Focus on center
col1, col2 = st.columns([2, 3])  # Asymmetric split
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])  # Dominant right
col1, col2 = st.columns([3, 1])  # Sidebar-like layout
col1, col2, col3 = st.columns([1, 3, 1])  # Center emphasis
```

**Container-Based Layouts:**

```python
# Group related content with custom styling
with st.container():
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown("### Section Title")

    col1, col2 = st.columns(2)
    with col1:
        st.write("Content left")
    with col2:
        st.write("Content right")

    st.markdown('</div>', unsafe_allow_html=True)
```

**Asymmetric Patterns:**

```python
# Hero + Sidebar Layout
col_sidebar, col_main = st.columns([1, 3])

with col_sidebar:
    st.markdown("### Navigation")
    # Filters, nav, settings

with col_main:
    st.markdown("# Main Content")
    # Primary content

# Dashboard Grid (different sized cards)
col1, col2 = st.columns([2, 1])
with col1:
    # Large primary chart
    st.line_chart(data)
with col2:
    # Two stacked metrics
    st.metric("KPI 1", "123")
    st.metric("KPI 2", "456")

# Magazine Layout
col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    st.markdown("## Featured Article")
    st.write("Long form content...")
with col2:
    st.markdown("### Side Info")
    st.write("Callout or aside")
with col3:
    st.markdown("## Related")
    st.write("Additional content")
```

**Spacing System:**

```css
/* Consistent spacing scale */
:root {
    --space-xs: 0.25rem;  /* 4px */
    --space-sm: 0.5rem;   /* 8px */
    --space-md: 1rem;     /* 16px */
    --space-lg: 1.5rem;   /* 24px */
    --space-xl: 2rem;     /* 32px */
    --space-2xl: 3rem;    /* 48px */
    --space-3xl: 4rem;    /* 64px */
}

/* Apply spacing */
.section {
    padding: var(--space-xl);
    margin-bottom: var(--space-2xl);
}

.card {
    padding: var(--space-lg);
    margin-bottom: var(--space-md);
}
```

### 3.4 Backgrounds & Visual Details

**Gradient Backgrounds:**

```css
/* Linear gradients */
.stApp {
    background: linear-gradient(180deg, #667EEA 0%, #764BA2 100%);
}

/* Radial gradients */
.hero-section {
    background: radial-gradient(circle at top right, #FF8C42, #FF6B9D);
}

/* Mesh gradient (trendy, sophisticated) */
.card {
    background:
        radial-gradient(at 40% 20%, hsla(28,100%,74%,1) 0px, transparent 50%),
        radial-gradient(at 80% 0%, hsla(189,100%,56%,1) 0px, transparent 50%),
        radial-gradient(at 0% 50%, hsla(355,100%,93%,1) 0px, transparent 50%),
        #FFFFFF;
}

/* Glass morphism */
.glass-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
```

**Pattern Overlays:**

```css
/* Dot pattern */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
    background-size: 20px 20px;
    pointer-events: none;
    z-index: -1;
}

/* Grid pattern */
.grid-bg {
    background-image:
        linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px);
    background-size: 20px 20px;
}

/* Diagonal stripes */
.striped-bg {
    background-image: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(0,0,0,0.05) 10px,
        rgba(0,0,0,0.05) 20px
    );
}
```

**Noise Texture:**

```css
/* Add subtle texture to prevent flat look */
.textured {
    position: relative;
}

.textured::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0.05;
    background-image: url('data:image/svg+xml;utf8,<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><filter id="noise"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(%23noise)"/></svg>');
    pointer-events: none;
}
```

### 3.5 Motion & Interactions

**CSS Transitions:**

```css
/* Smooth button hover */
.stButton > button {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}

/* Card lift on hover */
.card {
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 16px 48px rgba(0,0,0,0.2);
}

/* Color transition */
.badge {
    transition: background-color 0.2s ease, color 0.2s ease;
}

.badge:hover {
    background-color: var(--color-primary);
    color: white;
}
```

**Keyframe Animations:**

```css
/* Bounce effect */
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.metric-card:hover {
    animation: bounce 0.6s ease-in-out;
}

/* Pulse effect */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading-indicator {
    animation: pulse 2s infinite;
}

/* Slide in from left */
@keyframes slideInLeft {
    from {
        transform: translateX(-100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.notification {
    animation: slideInLeft 0.4s ease-out;
}

/* Fade in */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.page-content {
    animation: fadeIn 0.5s ease-in;
}

/* Shimmer loading */
@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}

.loading-skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 1000px 100%;
    animation: shimmer 2s infinite linear;
}
```

**Easing Functions:**

```css
/* Built-in easings */
transition: all 0.3s ease;        /* Slow start and end */
transition: all 0.3s ease-in;     /* Slow start */
transition: all 0.3s ease-out;    /* Slow end */
transition: all 0.3s ease-in-out; /* Slow start and end */
transition: all 0.3s linear;      /* Constant speed */

/* Custom cubic-bezier (more control) */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);  /* Material Design */
transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); /* Bounce */
transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* Back ease */
```

### 3.6 Components

**Enhanced Stat Cards:**

```python
def render_stat_card_enhanced(title, value, change=None, icon=None, color="primary"):
    """Render a stat card with enhanced styling."""
    color_map = {
        "primary": "var(--color-primary)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "error": "var(--color-error)",
        "info": "var(--color-info)"
    }

    bg_color = color_map.get(color, color_map["primary"])

    change_html = ""
    if change:
        change_icon = "▲" if change > 0 else "▼"
        change_color = "var(--color-success)" if change > 0 else "var(--color-error)"
        change_html = f'<span style="color: {change_color}; font-size: 0.9rem;">{change_icon} {abs(change)}%</span>'

    icon_html = f'<div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>' if icon else ""

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {bg_color}15 0%, {bg_color}05 100%);
        border-left: 4px solid {bg_color};
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    " class="hover-lift">
        {icon_html}
        <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.25rem;">
            {title}
        </div>
        <div style="color: var(--text-primary); font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem;">
            {value}
        </div>
        {change_html}
    </div>

    <style>
    .hover-lift:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }}
    </style>
    """, unsafe_allow_html=True)
```

**Custom Empty States:**

```python
def render_empty_state(icon, title, message, action_label=None, action_key=None):
    """Render a custom empty state with optional action."""
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 4rem 2rem;
        background: var(--color-bg);
        border-radius: 16px;
        border: 2px dashed var(--color-border);
    ">
        <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">
            {icon}
        </div>
        <h3 style="color: var(--text-primary); margin-bottom: 0.5rem; font-weight: 600;">
            {title}
        </h3>
        <p style="color: var(--text-secondary); margin-bottom: 2rem; max-width: 400px; margin-left: auto; margin-right: auto;">
            {message}
        </p>
    </div>
    """, unsafe_allow_html=True)

    if action_label and action_key:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            return st.button(action_label, key=action_key, type="primary", use_container_width=True)
    return False
```

**Progress Indicators:**

```python
def render_progress_ring(percentage, size=120, color="var(--color-primary)"):
    """Render a circular progress indicator."""
    circumference = 2 * 3.14159 * 45  # radius = 45
    offset = circumference - (percentage / 100 * circumference)

    st.markdown(f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <svg width="{size}" height="{size}" style="transform: rotate(-90deg);">
            <circle
                cx="{size/2}"
                cy="{size/2}"
                r="45"
                stroke="var(--color-border)"
                stroke-width="10"
                fill="none"
            />
            <circle
                cx="{size/2}"
                cy="{size/2}"
                r="45"
                stroke="{color}"
                stroke-width="10"
                fill="none"
                stroke-dasharray="{circumference}"
                stroke-dashoffset="{offset}"
                stroke-linecap="round"
                style="transition: stroke-dashoffset 0.5s ease;"
            />
        </svg>
        <div style="
            position: absolute;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        ">
            {percentage}%
        </div>
    </div>
    """, unsafe_allow_html=True)
```

**Badge Component:**

```python
def render_badge(text, variant="default"):
    """Render a styled badge."""
    variants = {
        "default": {"bg": "var(--color-border)", "color": "var(--text-primary)"},
        "primary": {"bg": "var(--color-primary)", "color": "white"},
        "success": {"bg": "var(--color-success)", "color": "white"},
        "warning": {"bg": "var(--color-warning)", "color": "var(--text-primary)"},
        "error": {"bg": "var(--color-error)", "color": "white"},
    }

    style = variants.get(variant, variants["default"])

    st.markdown(f"""
    <span style="
        display: inline-block;
        background: {style['bg']};
        color: {style['color']};
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    ">
        {text}
    </span>
    """, unsafe_allow_html=True)
```

---

## 4. Implementation Patterns

### 4.1 Custom CSS Integration

**Method 1: Load from File (Existing Pattern)**

```python
from admin.utils.ui_helpers import load_custom_css

# After st.set_page_config()
load_custom_css()
```

**Method 2: Inline CSS for Page-Specific Styles**

```python
st.markdown("""
<style>
/* Page-specific overrides */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
    border: none;
    color: white;
    font-weight: 600;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

/* Custom card class */
.feature-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
}

.feature-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)
```

**Method 3: CSS Variables for Theming**

```python
def apply_custom_theme(primary_color, secondary_color, bg_color):
    """Apply a custom color theme via CSS variables."""
    st.markdown(f"""
    <style>
    :root {{
        --color-primary: {primary_color};
        --color-secondary: {secondary_color};
        --color-bg: {bg_color};
    }}

    .stButton > button[kind="primary"] {{
        background: var(--color-primary);
    }}

    .stApp {{
        background: var(--color-bg);
    }}
    </style>
    """, unsafe_allow_html=True)

# Usage
apply_custom_theme("#FF8C42", "#6C63FF", "#F8F9FA")
```

### 4.2 Custom HTML Components

**Full Control with st.components.v1.html:**

```python
import streamlit.components.v1 as components

def render_custom_hero():
    """Render a custom hero section with full HTML/CSS/JS control."""
    components.html("""
    <div style="
        padding: 4rem 2rem;
        background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
        border-radius: 24px;
        color: white;
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
        text-align: center;
    ">
        <h1 style="
            font-family: 'Inter', sans-serif;
            font-size: 3rem;
            font-weight: 800;
            margin: 0 0 1rem 0;
            line-height: 1.2;
        ">
            Welcome to Your Dashboard
        </h1>
        <p style="
            font-size: 1.25rem;
            opacity: 0.9;
            margin: 0;
        ">
            Manage your data with confidence
        </p>
    </div>
    """, height=300)
```

**Interactive Components:**

```python
def render_interactive_chart():
    """Render an interactive chart with JavaScript."""
    components.html("""
    <div id="chart"></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const ctx = document.getElementById('chart');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                datasets: [{
                    label: 'Revenue',
                    data: [12, 19, 3, 5, 2],
                    borderColor: '#FF8C42',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
    </script>
    """, height=400)
```

### 4.3 Theme Management

**Existing Pattern from ui_helpers:**

```python
from admin.utils.ui_helpers import is_dark_mode, get_theme_colors

# Check theme
if is_dark_mode():
    st.markdown("### 🌙 Dark Mode Active")
else:
    st.markdown("### ☀️ Light Mode Active")

# Get theme colors
colors = get_theme_colors()
# Returns: {
#   'bg': '#F8F9FA',
#   'card_bg': '#FFFFFF',
#   'text_primary': '#2C3E50',
#   'text_secondary': '#6C757D',
#   'accent': '#FF8C42',
#   'border': '#DEE2E6',
#   ...
# }

# Use in components
st.markdown(f"""
<div style="
    background-color: {colors['card_bg']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border']};
    padding: 1rem;
    border-radius: 8px;
">
    Themed content
</div>
""", unsafe_allow_html=True)
```

**Toggle Theme Button:**

```python
# In sidebar or page
if st.button("🌓 Toggle Theme"):
    current = st.session_state.get('theme', 'light')
    st.session_state.theme = 'dark' if current == 'light' else 'light'
    st.rerun()
```

### 4.4 Responsive Design

**Mobile-Friendly Layouts:**

```css
/* Desktop: 3 columns */
@media (min-width: 768px) {
    .grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }
}

/* Tablet: 2 columns */
@media (max-width: 767px) and (min-width: 480px) {
    .grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }
}

/* Mobile: 1 column */
@media (max-width: 479px) {
    .grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 1rem;
    }

    /* Adjust font sizes */
    h1 { font-size: 2rem; }
    h2 { font-size: 1.5rem; }

    /* Stack columns */
    .stColumns {
        flex-direction: column;
    }
}
```

---

## 5. Anti-Patterns to Avoid

### ❌ Generic AI Aesthetics

**DO NOT use these overused patterns:**
- Purple gradients on white backgrounds (everywhere in AI tools)
- Inter font for everything (boring, no personality)
- Equal-width columns everywhere (lazy, no visual hierarchy)
- Default Streamlit blue (#FF4B4B)
- Centered everything with no structure
- Blue + white + gray color schemes (corporate blandness)
- No custom styling whatsoever (default Streamlit look)
- Timid, low-contrast colors (looks unfinished)
- Space Grotesk font (overhyped)

### ❌ Poor Color Choices

**Avoid:**
- Random colors without system or meaning
- Status colors that don't meet WCAG standards (contrast ratios)
- Using too many colors (> 5 in palette)
- Colors that clash or fight for attention
- Ignoring color psychology (red for success, green for errors)

**Do Instead:**
- Define a clear palette with purpose
- Test contrast ratios (WCAG AA minimum: 4.5:1 for text)
- Use color consistently (primary = primary actions everywhere)
- Consider color blindness (use icons + color, not just color)

### ❌ Typography Mistakes

**Avoid:**
- System fonts without customization (looks lazy)
- Mixing 4+ font families (chaotic, unprofessional)
- Poor hierarchy (all text same size/weight)
- Unreadable line heights (< 1.4 for body text)
- Tiny text (< 14px for body)
- ALL CAPS FOR EVERYTHING (hard to read)
- Centered paragraphs (hard to scan)

**Do Instead:**
- Choose 1-2 fonts (display + body)
- Create clear hierarchy with size, weight, color
- Use appropriate line heights (1.6-1.8 for body)
- Left-align paragraphs, center only headlines
- Use sentence case for readability

### ❌ Layout Issues

**Avoid:**
- No whitespace (cramped, overwhelming)
- Too much whitespace (empty, unfinished)
- Inconsistent spacing (10px here, 15px there, 8px over there)
- Everything in a single column (boring, no structure)
- Cramped forms and inputs (labels touching inputs)
- No visual grouping (related items far apart)

**Do Instead:**
- Use a spacing scale (8px, 16px, 24px, 32px...)
- Group related content with containers
- Use asymmetric column layouts
- Give inputs breathing room

### ❌ Motion Mistakes

**Avoid:**
- Animations longer than 0.5s (feels slow)
- Too many animations (distracting)
- Animations without purpose (motion for motion's sake)
- Janky animations (not GPU-accelerated)
- No easing (linear motion feels robotic)

**Do Instead:**
- Keep animations < 0.3s for UI interactions
- Use animations to guide attention or provide feedback
- Use transform and opacity (GPU-accelerated)
- Apply appropriate easing (ease-out for entrances, ease-in for exits)

---

## 6. Streamlit Constraints & Creative Solutions

| Constraint | Creative Solution |
|------------|-------------------|
| **Limited layout flexibility** | Use CSS Grid/Flexbox with custom classes; absolute/fixed positioning for overlays; nested columns for complex layouts |
| **No native animations** | CSS @keyframes and transitions; st.components for complex interactions; strategic use of st.rerun() |
| **Server-side rendering** | CSS-driven interactions (hover, focus); session state for stateful UX; minimize unnecessary reruns |
| **Component customization limits** | Target Streamlit test IDs with CSS (`[data-testid="..."]`); wrap in custom HTML with st.markdown |
| **Form styling limits** | Wrap forms in custom containers; style inputs with CSS selectors; use custom HTML for complex forms |
| **No native modals** | Use st.dialog (Streamlit 1.31+) or custom HTML overlays with st.components; fixed position divs |
| **Limited animation control** | Combine CSS animations with st.rerun() for stateful animations; use st.components for complex animations |
| **No native dark mode toggle** | Implement with session state + CSS variables; use data attributes for theming |

---

## 7. Design Complexity Matching

Implementation complexity must match aesthetic ambition.

### Maximalist/Bold Designs

**Characteristics:**
- Elaborate CSS (300+ lines)
- Multiple animations and transitions
- Rich typography with custom fonts
- Layered backgrounds and effects
- Bold, saturated colors
- Extensive use of gradients and shadows
- Complex layouts with overlapping elements

**When to Use:**
- Creative tools and experimental UIs
- Marketing or portfolio pages
- Data storytelling apps
- When "wow factor" is important

**Example Implementation:**
```css
/* Elaborate, multi-layered */
.hero {
    background:
        radial-gradient(at top right, rgba(255,140,66,0.3), transparent),
        radial-gradient(at bottom left, rgba(108,99,255,0.3), transparent),
        linear-gradient(135deg, #667EEA, #764BA2);
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: url('pattern.svg');
    opacity: 0.1;
    animation: float 20s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-20px) rotate(5deg); }
}
```

### Minimalist/Refined Designs

**Characteristics:**
- Precise spacing (every pixel matters)
- Subtle micro-interactions
- 1-2 carefully chosen fonts
- Limited color palette (2-3 colors)
- Generous whitespace
- Clean, geometric shapes
- Restrained use of shadows

**When to Use:**
- Professional dashboards
- Data-focused applications
- When clarity is paramount
- Executive or client-facing tools

**Example Implementation:**
```css
/* Precise, restrained */
.card {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 24px;
    transition: border-color 0.2s ease;
}

.card:hover {
    border-color: #3B82F6;
}

h1 {
    font-family: 'Inter', sans-serif;
    font-size: 32px;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.25;
    margin-bottom: 8px;
}
```

### Data-Driven/Functional Designs

**Characteristics:**
- Clear visual hierarchy
- WCAG AAA contrast ratios
- Readable fonts (large body text)
- Effective use of color for meaning
- Accessible interactions
- Performance-optimized
- Mobile-responsive

**When to Use:**
- Admin tools and internal apps
- Analytics dashboards
- Data exploration tools
- When accessibility is critical

**Example Implementation:**
```css
/* Functional, accessible */
:root {
    --text-primary: #1F2937;  /* 16:1 contrast */
    --text-secondary: #4B5563; /* 7:1 contrast */
    --bg-primary: #FFFFFF;
}

body {
    font-family: system-ui, sans-serif;
    font-size: 16px;
    line-height: 1.6;
    color: var(--text-primary);
}

.button {
    min-height: 44px; /* Touch target size */
    padding: 12px 24px;
    font-size: 16px;
    font-weight: 500;
    background: #3B82F6;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.button:focus-visible {
    outline: 3px solid #93C5FD;
    outline-offset: 2px;
}
```

---

## 8. Aesthetic Direction Examples

### Example 1: Brutalist Data Lab

**Aesthetic:** Raw, utilitarian, monospace, stark contrasts
**When to Use:** Developer tools, system monitoring, logs, technical dashboards

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

:root {
    --brutalist-black: #000000;
    --brutalist-white: #FFFFFF;
    --brutalist-red: #FF0000;
    --font-mono: 'JetBrains Mono', monospace;
}

.stApp {
    background: var(--brutalist-white);
    font-family: var(--font-mono);
    color: var(--brutalist-black);
}

h1, h2, h3 {
    font-family: var(--font-mono);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    border: 3px solid var(--brutalist-black);
    padding: 1rem;
    background: var(--brutalist-black);
    color: var(--brutalist-white);
    margin-bottom: 2rem;
}

.stButton > button {
    font-family: var(--font-mono);
    background: var(--brutalist-red);
    color: var(--brutalist-white);
    border: 3px solid var(--brutalist-black);
    border-radius: 0;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    padding: 1rem 2rem;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: var(--brutalist-black);
    color: var(--brutalist-red);
}

[data-testid="stMetric"] {
    border: 3px solid var(--brutalist-black);
    border-radius: 0;
    background: var(--brutalist-white);
    padding: 1rem;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-mono);
    font-weight: 700;
    color: var(--brutalist-red);
}

.stDataFrame {
    border: 3px solid var(--brutalist-black);
    font-family: var(--font-mono);
}
</style>
""", unsafe_allow_html=True)

st.markdown("# SYSTEM MONITOR")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("CPU", "87%", "+12%")
with col2:
    st.metric("MEMORY", "4.2 GB", "-0.3 GB")
with col3:
    st.metric("DISK", "234 GB", "+15 GB")
```

### Example 2: Editorial Magazine

**Aesthetic:** Sophisticated, hierarchical, serif elegance
**When to Use:** Report viewers, content apps, narrative data, editorial interfaces

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Serif+Pro:wght@400;600&display=swap');

:root {
    --editorial-black: #1A1A1A;
    --editorial-cream: #F5F3EE;
    --editorial-burgundy: #8B2635;
    --editorial-gold: #D4AF37;
    --font-display: 'Playfair Display', serif;
    --font-body: 'Source Serif Pro', serif;
}

.stApp {
    background: var(--editorial-cream);
    color: var(--editorial-black);
    font-family: var(--font-body);
    font-size: 1.1rem;
    line-height: 1.7;
}

h1 {
    font-family: var(--font-display);
    font-size: 4rem;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 0.5rem;
    color: var(--editorial-burgundy);
    letter-spacing: -0.03em;
}

h2 {
    font-family: var(--font-display);
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--editorial-black);
    margin-top: 3rem;
    margin-bottom: 1rem;
    border-bottom: 2px solid var(--editorial-gold);
    padding-bottom: 0.5rem;
}

h3 {
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--editorial-burgundy);
}

.stMarkdown p:first-of-type::first-letter {
    font-size: 3.5rem;
    font-weight: 900;
    line-height: 1;
    float: left;
    margin-right: 0.5rem;
    margin-top: 0.1rem;
    color: var(--editorial-burgundy);
    font-family: var(--font-display);
}

.stButton > button {
    font-family: var(--font-body);
    background: var(--editorial-burgundy);
    color: var(--editorial-cream);
    border: none;
    border-radius: 0;
    padding: 0.75rem 2rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-size: 0.875rem;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background: var(--editorial-black);
}

[data-testid="stMetric"] {
    background: white;
    border-left: 3px solid var(--editorial-gold);
    padding: 1.5rem;
    border-radius: 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("# The Quarterly Review")
st.markdown("## Financial Performance Analysis")
st.write("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
```

### Example 3: Organic/Natural

**Aesthetic:** Soft, flowing, rounded, earth tones
**When to Use:** Health apps, environmental data, human-centered tools, wellness dashboards

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');

:root {
    --organic-sage: #8FB996;
    --organic-sand: #E6D5B8;
    --organic-terracotta: #D4756C;
    --organic-cream: #FAF8F5;
    --organic-forest: #4A6B5A;
    --font-main: 'Outfit', sans-serif;
}

.stApp {
    background: linear-gradient(180deg, var(--organic-cream) 0%, var(--organic-sand) 100%);
    font-family: var(--font-main);
}

h1, h2, h3 {
    font-family: var(--font-main);
    color: var(--organic-forest);
    font-weight: 600;
}

h1 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.stButton > button {
    background: var(--organic-sage);
    color: white;
    border: none;
    border-radius: 24px;
    padding: 0.75rem 2rem;
    transition: all 0.3s ease;
    font-family: var(--font-main);
    font-weight: 600;
}

.stButton > button:hover {
    background: var(--organic-terracotta);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(212, 117, 108, 0.3);
}

[data-testid="stMetric"] {
    background: rgba(250, 248, 245, 0.8);
    backdrop-filter: blur(10px);
    border-radius: 24px;
    border: 2px solid rgba(143, 185, 150, 0.2);
    padding: 1.5rem;
    transition: all 0.3s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(143, 185, 150, 0.2);
}

[data-testid="stMetricValue"] {
    color: var(--organic-forest);
}

.stDataFrame {
    border-radius: 16px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

st.markdown("# Wellness Dashboard")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Steps Today", "8,432", "+1,234")
with col2:
    st.metric("Active Minutes", "45", "+12")
with col3:
    st.metric("Calories", "1,876", "-124")
```

### Example 4: Cyberpunk/Neon

**Aesthetic:** Dark, neon accents, futuristic
**When to Use:** Gaming dashboards, creative tools, tech demos, immersive experiences

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&display=swap');

:root {
    --cyber-bg: #0A0E27;
    --cyber-card: #1A1F3A;
    --cyber-cyan: #00F0FF;
    --cyber-magenta: #FF006E;
    --cyber-purple: #8338EC;
    --font-display: 'Orbitron', sans-serif;
    --font-body: 'Rajdhani', sans-serif;
}

.stApp {
    background: var(--cyber-bg);
    color: var(--cyber-cyan);
    font-family: var(--font-body);
    position: relative;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image:
        repeating-linear-gradient(0deg, rgba(0,240,255,0.03) 0px, transparent 1px, transparent 2px, rgba(0,240,255,0.03) 3px),
        repeating-linear-gradient(90deg, rgba(0,240,255,0.03) 0px, transparent 1px, transparent 2px, rgba(0,240,255,0.03) 3px);
    background-size: 20px 20px;
    pointer-events: none;
    z-index: 1;
}

h1, h2, h3 {
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--cyber-cyan);
    text-shadow: 0 0 20px var(--cyber-cyan);
}

h1 {
    font-size: 3rem;
    font-weight: 900;
    animation: glitch 5s infinite;
}

@keyframes glitch {
    0%, 100% { text-shadow: 0 0 20px var(--cyber-cyan); }
    50% { text-shadow: 0 0 20px var(--cyber-magenta), 0 0 40px var(--cyber-magenta); }
}

.stButton > button {
    background: linear-gradient(135deg, var(--cyber-purple), var(--cyber-magenta));
    color: white;
    border: 2px solid var(--cyber-cyan);
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 2px;
    box-shadow: 0 0 20px var(--cyber-cyan);
    transition: all 0.3s ease;
    padding: 0.75rem 2rem;
}

.stButton > button:hover {
    box-shadow: 0 0 40px var(--cyber-magenta);
    transform: translateY(-3px);
}

[data-testid="stMetric"] {
    background: var(--cyber-card);
    border: 2px solid var(--cyber-cyan);
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
    border-radius: 8px;
    padding: 1.5rem;
}

[data-testid="stMetricValue"] {
    color: var(--cyber-cyan);
    font-family: var(--font-display);
    text-shadow: 0 0 10px var(--cyber-cyan);
}
</style>
""", unsafe_allow_html=True)

st.markdown("# SYSTEM OVERRIDE")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("NEURAL LOAD", "78%", "+5%")
with col2:
    st.metric("BANDWIDTH", "2.4 TB/s", "+0.3 TB/s")
with col3:
    st.metric("NODES ACTIVE", "12,456", "+234")
```

---

## 9. Complete Code Examples

### Example 1: Custom Dashboard Page

```python
"""
Custom Dashboard with Distinctive Design
Demonstrates: Custom CSS, themed components, creative layout, animations
"""
import streamlit as st
from admin.utils.ui_helpers import load_custom_css, get_theme_colors

st.set_page_config(
    page_title="Custom Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load base CSS
load_custom_css()

# Add page-specific custom styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;600&display=swap');

.hero-section {
    background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
    padding: 3rem 2rem;
    border-radius: 24px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    animation: rotate 20s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.2;
    position: relative;
    z-index: 1;
}

.hero-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 1.2rem;
    opacity: 0.9;
    margin-top: 0.5rem;
    position: relative;
    z-index: 1;
}

.stat-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
    border-left: 4px solid #667EEA;
}

.stat-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.15);
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 2rem;
}

.feature-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, transparent 100%);
    opacity: 0;
    transition: opacity 0.4s ease;
}

.feature-card:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 16px 48px rgba(0,0,0,0.15);
}

.feature-card:hover::before {
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">Welcome Back, User</h1>
    <p class="hero-subtitle">Here's what's happening with your data today</p>
</div>
""", unsafe_allow_html=True)

# Metrics with creative layout
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

with col1:
    st.metric("Total Records", "12.5K", "+2.3K", delta_color="normal")

with col2:
    st.metric("Success Rate", "98.7%", "+1.2%", delta_color="normal")

with col3:
    st.metric("Active Jobs", "8", "-2", delta_color="inverse")

with col4:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(40,167,69,0.1) 0%, rgba(40,167,69,0.05) 100%);
        border-left: 4px solid #28A745;
        border-radius: 12px;
        padding: 1.5rem;
    ">
        <h3 style="margin: 0 0 0.5rem 0; color: #28A745;">System Health</h3>
        <p style="margin: 0; color: #6C757D;">All systems operational • Last check: 2 min ago</p>
    </div>
    """, unsafe_allow_html=True)

# Spacer
st.markdown("<div style='margin: 3rem 0;'></div>", unsafe_allow_html=True)

# Feature grid
st.markdown("## Key Features")

st.markdown("""
<div class="feature-grid">
    <div class="feature-card">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">⚡</div>
        <h3 style="margin-bottom: 0.5rem; color: #2C3E50;">Fast Import</h3>
        <p style="color: #6C757D; line-height: 1.6;">
            Process thousands of records in seconds with our optimized ETL pipeline.
        </p>
    </div>

    <div class="feature-card">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">✓</div>
        <h3 style="margin-bottom: 0.5rem; color: #2C3E50;">Smart Validation</h3>
        <p style="color: #6C757D; line-height: 1.6;">
            Automatic data quality checks ensure your imports are always correct.
        </p>
    </div>

    <div class="feature-card">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">📊</div>
        <h3 style="margin-bottom: 0.5rem; color: #2C3E50;">Real-time Monitoring</h3>
        <p style="color: #6C757D; line-height: 1.6;">
            Watch your jobs execute live with detailed progress tracking.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)
```

### Example 2: Animated Feature Card Component

```python
def render_animated_feature_card(title, description, icon, color="#667EEA"):
    """
    Render a feature card with hover animations and custom styling.

    Args:
        title: Card title
        description: Card description text
        icon: Emoji or icon to display
        color: Accent color (hex code)
    """
    st.markdown(f"""
    <style>
    .feature-card-{id(title)} {{
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border-left: 4px solid {color};
        position: relative;
        overflow: hidden;
        height: 100%;
    }}

    .feature-card-{id(title)}::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, {color}22 0%, transparent 100%);
        opacity: 0;
        transition: opacity 0.4s ease;
    }}

    .feature-card-{id(title)}:hover {{
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(0,0,0,0.15);
        border-left-width: 8px;
    }}

    .feature-card-{id(title)}:hover::before {{
        opacity: 1;
    }}

    .feature-icon-{id(title)} {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        display: inline-block;
        transition: transform 0.4s ease;
    }}

    .feature-card-{id(title)}:hover .feature-icon-{id(title)} {{
        transform: scale(1.2) rotate(5deg);
    }}

    .feature-title-{id(title)} {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #2C3E50;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }}

    .feature-description-{id(title)} {{
        color: #6C757D;
        line-height: 1.6;
        position: relative;
        z-index: 1;
    }}
    </style>

    <div class="feature-card-{id(title)}">
        <div class="feature-icon-{id(title)}">{icon}</div>
        <h3 class="feature-title-{id(title)}">{title}</h3>
        <p class="feature-description-{id(title)}">{description}</p>
    </div>
    """, unsafe_allow_html=True)


# Usage Example
st.markdown("## Our Features")

col1, col2, col3 = st.columns(3)

with col1:
    render_animated_feature_card(
        title="Lightning Fast",
        description="Process thousands of records in seconds with our optimized ETL pipeline.",
        icon="⚡",
        color="#FFD700"
    )

with col2:
    render_animated_feature_card(
        title="Smart Validation",
        description="Automatic data quality checks ensure your imports are always correct.",
        icon="✓",
        color="#00C853"
    )

with col3:
    render_animated_feature_card(
        title="Live Monitoring",
        description="Watch your jobs execute in real-time with detailed progress tracking.",
        icon="📊",
        color="#FF6B9D"
    )
```

---

## 10. Integration with Existing Skills

This skill works alongside existing Tangerine patterns:

### With Streamlit-Admin

**Streamlit-Admin provides:**
- Page structure and navigation
- Form patterns and validation
- Service layer integration
- Session state management
- Reusable components (tables, notifications)

**Streamlit-Design adds:**
- Custom CSS and visual identity
- Unique aesthetic direction
- Enhanced components with animations
- Brand-specific color schemes
- Typography and layout customization

**Example Integration:**

```python
"""
Import Config Management Page
Structure from streamlit-admin, design from streamlit-design
"""
import streamlit as st
from admin.components.forms import render_config_form
from admin.services.import_config_service import get_all, create, update, delete
from admin.utils.ui_helpers import load_custom_css

# streamlit-admin: Page config
st.set_page_config(page_title="Import Configs", page_icon="⚙️", layout="wide")

# streamlit-design: Custom styling
load_custom_css()
st.markdown("""
<style>
/* Page-specific design enhancements */
.config-card {
    border-left: 4px solid var(--color-primary);
    transition: all 0.3s ease;
}
.config-card:hover {
    transform: translateX(8px);
}
</style>
""", unsafe_allow_html=True)

# streamlit-admin: Service layer call
configs = get_all()

# streamlit-design: Enhanced presentation
st.markdown("# Import Configurations")
st.markdown("Manage your data import pipelines with ease")

# Continue with streamlit-admin patterns...
```

### With Service-Developer

**Design layer never compromises separation of concerns:**
- Pages still call services (not raw SQL)
- UI helpers remain in `utils/`, not `services/`
- Business logic stays in service layer
- Design is purely presentational

### With Database-Operations

**Visual design doesn't affect data integrity:**
- Forms still validate before service calls
- Pretty interfaces still use parameterized queries
- Database schema remains normalized
- Data integrity rules are enforced

---

## 11. Pre-Implementation Checklist

### Before Writing Code

- [ ] **Answered all 4 design thinking questions:**
  - [ ] Purpose (problem, users, goal)
  - [ ] Tone (chosen aesthetic direction)
  - [ ] Constraints (performance, accessibility, time)
  - [ ] Differentiation (one memorable thing)

- [ ] **Chosen 1-2 distinctive fonts** (not defaults, not overused)
- [ ] **Defined color palette** (3-5 colors + neutrals, with purpose)
- [ ] **Sketched layout approach** (asymmetric? grid? creative columns?)
- [ ] **Identified key micro-interactions** (hover states, transitions)

### During Implementation

- [ ] **Created CSS variables** for consistency (colors, spacing, fonts)
- [ ] **Added dark mode support** (if applicable, using existing patterns)
- [ ] **Implemented hover states and transitions** (smooth, purposeful)
- [ ] **Used creative column ratios** (not all equal widths)
- [ ] **Added visual details** (gradients, shadows, borders, patterns)
- [ ] **Tested in browser** (not just Streamlit preview)

### Before Finalizing

- [ ] **Tested in both light and dark mode** (if applicable)
- [ ] **Checked WCAG contrast ratios** (use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/))
  - [ ] Normal text: 4.5:1 minimum (AA)
  - [ ] Large text (18pt+): 3:1 minimum (AA)
- [ ] **Verified mobile responsiveness** (< 768px width)
- [ ] **Removed "AI slop" indicators:**
  - [ ] No generic purple gradients
  - [ ] No Inter font everywhere
  - [ ] No equal-width columns everywhere
  - [ ] No default colors
- [ ] **Confirmed design matches context and purpose**
- [ ] **Verified performance** (no janky animations, fast load times)

---

## 12. When to Use This Skill vs. Default Tangerine Theme

### Use Streamlit-Design When:

- Building a **new page** that needs unique visual identity
- Creating **customer-facing** dashboards or reports
- **Experimenting** with new UI patterns
- Task explicitly mentions **"design"**, **"beautiful"**, **"distinctive"**, **"custom styling"**
- User asks to **"make it look better"** or **"improve the UI"**
- The interface needs to **convey a specific brand** or aesthetic
- You want to **stand out** from generic admin panels

### Stick with Default Tangerine Theme When:

- Making **quick admin pages** for internal use
- **Functionality is the priority** (just get it working)
- **Time constraints** (ship fast, iterate later)
- User explicitly wants **consistency** with existing pages
- The page is **purely functional** (logs, system monitoring)
- **Prototyping** or **proof of concept** work

---

## 13. Progressive Enhancement Approach

**Don't try to implement everything at once. Ship and iterate.**

### Phase 1: Foundation (Streamlit-Admin)
- Use streamlit-admin patterns
- Structure pages correctly
- Implement forms and services
- Basic functionality works

### Phase 2: Theme (Tangerine CSS)
- Apply base Tangerine theme
- Industrial aesthetic baseline
- Consistent with existing pages

### Phase 3: Customize (Streamlit-Design)
- Add page-specific CSS
- Choose distinctive fonts
- Apply custom color palette
- Create unique identity

### Phase 4: Refine (Polish)
- Add animations and transitions
- Create custom components
- Implement micro-interactions
- Enhance user experience

### Phase 5: Perfect (Accessibility + Responsive)
- Dark mode support
- WCAG compliance
- Mobile responsiveness
- Performance optimization

---

## 14. Resources & Inspiration

### Fonts
- [Google Fonts](https://fonts.google.com) - Free font library
- [Font Pair](https://fontpair.co) - Font pairing suggestions
- [Typ.io](https://typ.io) - Font inspiration from real sites

### Colors
- [Coolors](https://coolors.co) - Color palette generator
- [Color Hunt](https://colorhunt.co) - Curated color palettes
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - WCAG compliance
- [Paletton](https://paletton.com) - Color scheme designer

### Gradients
- [CSS Gradient](https://cssgradient.io) - Gradient generator
- [UI Gradients](https://uigradients.com) - Beautiful gradients

### Patterns & Textures
- [Hero Patterns](https://heropatterns.com) - Free SVG patterns
- [Pattern Pad](https://patternpad.com) - Pattern designer
- [Subtle Patterns](https://www.toptal.com/designers/subtlepatterns/) - Texture library

### Design Inspiration
- [Dribbble](https://dribbble.com) - Design showcase
- [Behance](https://behance.net) - Creative work
- [Awwwards](https://awwwards.com) - Web design excellence

---

## 15. Skill Activation

This skill activates when user asks to:
- "Create a dashboard" or "build a page"
- "Make it look better" or "improve the design"
- "Add custom styling" or "customize the UI"
- "Create something distinctive" or "unique interface"
- "Design a [page/component/interface]"
- Mentions aesthetic keywords: "beautiful", "elegant", "modern", "bold"

---

## Final Notes

### Philosophy
- **Design thinking comes BEFORE code** (Purpose, Tone, Constraints, Differentiation)
- **Generic AI aesthetics are easy to spot and should be avoided**
- **Distinctive doesn't mean complex** - minimalism can be bold too
- **Every design decision should be intentional**
- **Context matters** - design for the user and use case

### Remember
- Streamlit apps can be **beautiful AND functional**
- Good design **enhances** usability, not distracts from it
- **Bold choices** are better than safe choices
- **Consistency** within a page/app is more important than novelty
- **Accessibility** is non-negotiable (WCAG standards)

### When in Doubt
1. Ask the 4 design thinking questions
2. Look at the examples in this skill
3. Start simple, enhance iteratively
4. Test with real users
5. Iterate based on feedback

---

**Now go create something distinctive. 🎨**
