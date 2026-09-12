"""Entry point for ``python -m bquant``.

The console script (``bquant``) and this module are the same entry point, not two
implementations: both call :func:`bquant.cli.main`. The ``-m`` form exists because it
is what people reach for when the console script is not on PATH — a fresh venv that
was not activated, a Windows shell, a container. Until 0.0.19 it exited with rc 1 and
a ``No module named bquant.__main__`` message, which reads as "the package is broken"
rather than "that form is not supported".

Nothing is duplicated here on purpose: a second copy of the argument parsing would be
a second literal to keep in step with the first, and that is the defect this project
has closed three times (G8, G32, G33).
"""

from bquant.cli import main

if __name__ == "__main__":
    main()
