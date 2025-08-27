# BQuant Documentation

This directory contains the documentation for the BQuant project, built with Sphinx.

## 📚 Documentation Structure

- `api/` - API documentation
- `user_guide/` - User guides and tutorials
- `developer_guide/` - Developer documentation
- `tutorials/` - Step-by-step tutorials
- `examples/` - Code examples
- `_static/` - Static files (CSS, JS, images)
- `_templates/` - Custom templates

## 🚀 Local Development

### Prerequisites

Install documentation dependencies:

```bash
pip install -r requirements-docs.txt
```

### Building Documentation

```bash
# Build HTML documentation
cd docs
make html

# Or using sphinx directly
sphinx-build -b html . _build/html
```

### Viewing Documentation

After building, open `docs/_build/html/index.html` in your browser.

## 🌐 Read the Docs Setup

### Automatic Setup

1. **Push to GitHub**: Ensure your repository is on GitHub
2. **Connect to Read the Docs**:
   - Go to [readthedocs.org](https://readthedocs.org)
   - Sign in with your GitHub account
   - Click "Import a Project"
   - Select your `bquant` repository
   - Read the Docs will automatically detect the `.readthedocs.yml` configuration

### Manual Setup

If automatic setup doesn't work:

1. **Create Project on Read the Docs**:
   - Go to [readthedocs.org](https://readthedocs.org)
   - Click "Create Project"
   - Connect your GitHub repository
   - Set project name: `bquant`
   - Set documentation type: `Sphinx`
   - Set configuration file: `.readthedocs.yml`

2. **Configure Build Settings**:
   - Python version: 3.13
   - Install project: Yes
   - Install dependencies: Yes
   - Requirements file: `requirements-docs.txt`

### Configuration Files

- `.readthedocs.yml` - Read the Docs configuration
- `docs/conf.py` - Sphinx configuration
- `requirements-docs.txt` - Documentation dependencies

## 📖 Documentation Features

- **Auto-generated API docs** from docstrings
- **Search functionality**
- **Mobile-responsive design**
- **PDF and ePub exports**
- **Version control** (multiple versions)
- **GitHub integration**

## 🔧 Customization

### Adding New Pages

1. Create `.rst` or `.md` files in appropriate directories
2. Add them to the navigation in `index.rst`
3. Rebuild documentation

### Styling

- Custom CSS: `_static/custom.css`
- Custom templates: `_templates/`
- Theme: `sphinx_rtd_theme`

### Extensions

Current extensions:
- `sphinx.ext.autodoc` - Auto-generate API docs
- `sphinx.ext.napoleon` - Google/NumPy docstring support
- `sphinx.ext.viewcode` - Link to source code
- `sphinx.ext.githubpages` - GitHub Pages support
- `sphinx.ext.intersphinx` - Link to other docs
- `sphinx.ext.mathjax` - Math rendering
- `sphinx_copybutton` - Copy code blocks
- `myst_parser` - Markdown support

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **Build failures**: Check Python version compatibility
3. **Missing modules**: Verify `sys.path` in `conf.py`

### Read the Docs Issues

1. **404 Project not found**: 
   - Ensure project is imported on Read the Docs
   - Check repository visibility (public)
   - Verify project name matches exactly

2. **Build failures**:
   - Check build logs on Read the Docs
   - Verify `.readthedocs.yml` syntax
   - Ensure all dependencies are available

3. **Version issues**:
   - Update version in `pyproject.toml`
   - Update version in `docs/conf.py`
   - Tag releases in GitHub

## 📝 Contributing

1. Write documentation in `.rst` or `.md` format
2. Follow Sphinx conventions
3. Test locally before pushing
4. Update navigation if adding new sections

## 🔗 Links

- **Live Documentation**: https://bquant.readthedocs.io/
- **Read the Docs**: https://readthedocs.org/
- **Sphinx Documentation**: https://www.sphinx-doc.org/
- **GitHub Repository**: https://github.com/kogriv/bquant
