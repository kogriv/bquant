# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Custom targets for BQuant documentation

# Build HTML documentation
html:
	@echo "Building HTML documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "HTML documentation built in $(BUILDDIR)/html/"

# Build PDF documentation
pdf:
	@echo "Building PDF documentation..."
	@$(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "PDF documentation built in $(BUILDDIR)/latex/"

# Build EPUB documentation
epub:
	@echo "Building EPUB documentation..."
	@$(SPHINXBUILD) -M epub "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "EPUB documentation built in $(BUILDDIR)/epub/"

# Clean build directory
clean:
	@echo "Cleaning build directory..."
	@rm -rf "$(BUILDDIR)"
	@echo "Build directory cleaned."

# Serve documentation locally
serve: html
	@echo "Starting local server..."
	@cd "$(BUILDDIR)/html" && python -m http.server 8000
	@echo "Documentation available at http://localhost:8000"

# Check for broken links
linkcheck:
	@echo "Checking for broken links..."
	@$(SPHINXBUILD) -M linkcheck "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Spell check
spelling:
	@echo "Running spell check..."
	@$(SPHINXBUILD) -M spelling "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Full documentation build (HTML, PDF, EPUB)
all: clean html pdf epub
	@echo "All documentation formats built successfully."

# Quick build for development
dev: html
	@echo "Development build completed."
