# Cursor Rules for BQuant

This directory contains Cursor rules that help AI assistants understand and work with the BQuant project codebase.

## Available Rules

### 1. `project-overview.mdc` (Always Applied)
- Provides high-level understanding of the BQuant project
- Describes detailed architecture and key modules
- Lists key design patterns and development guidelines

### 2. `python-coding-standards.mdc` (Python Files)
- Defines Python coding standards and style guidelines
- Covers import organization, documentation, and error handling
- Includes performance considerations

### 3. `data-handling.mdc` (Data-Related Files)
- Guidelines for data loading, processing, and validation
- Supported data sources (OANDA, MetaTrader) and formats
- Timeframe conventions and column standards
- Critical rules about using sample data

### 4. `indicators-and-analysis.mdc` (Indicator & Analysis Files)
- Standards for developing technical indicators
- MACD analysis and zone detection guidelines
- Analysis engine implementation and research scripts
- Performance optimization and extensibility

### 5. `visualization.mdc` (Visualization & Analysis Scripts)
- Chart creation and styling guidelines
- Plotting library usage (Plotly, Matplotlib)
- Export and performance considerations

### 6. `testing-and-quality.mdc` (All Python Files)
- Testing standards and coverage requirements
- Code quality tools and practices
- CI/CD integration guidelines

### 7. `development-workflow.mdc` (Always Applied)
- Development environment setup and workflow
- Release process and changelog management
- Critical development rules and troubleshooting

### 8. `research-scripts.mdc` (Research & Analysis Scripts)
- NotebookSimulator pattern implementation
- Step-by-step execution and CLI integration
- Error handling and performance monitoring
- Best practices for research scripts

### 9. `configuration-patterns.mdc` (All Python Files)
- Centralized configuration system usage
- Performance monitoring and caching patterns
- Logging and exception handling patterns
- Configuration best practices

## How to Use

These rules are automatically applied by Cursor based on:
- **Always Apply**: Rules that apply to every request
- **Globs**: Rules that apply to specific file types or directories
- **Description**: Rules that can be manually fetched when needed

## Key Design Patterns Covered

- **NotebookSimulator Pattern**: For research scripts with step-by-step execution
- **Configuration Pattern**: Centralized configuration management
- **Sample Data Pattern**: Always use embedded sample data
- **Performance Monitoring**: Built-in performance tracking
- **Caching Pattern**: Two-level caching system
- **Error Handling**: Custom exception hierarchy

## Adding New Rules

To create a new rule:
1. Create a `.mdc` file in this directory
2. Use proper frontmatter with metadata
3. Follow the existing rule format and structure
4. Test the rule with AI assistants

## Rule Format

```markdown
---
alwaysApply: true  # or false
globs: *.py        # file patterns
description: "Rule description"  # for manual fetching
---

# Rule Title
Rule content and guidelines...
```

## Benefits

- **Consistency**: Ensures all AI interactions follow project standards
- **Efficiency**: Reduces need to explain project structure repeatedly
- **Quality**: Maintains coding standards and best practices
- **Onboarding**: Helps new developers understand project conventions
- **Pattern Recognition**: Provides clear examples of key design patterns
