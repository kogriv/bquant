from pathlib import Path
import sys
import inspect


def _resolve_default_output_dir() -> Path:
    """Compute default output directory: outputs/vis/<script_name> under CWD.

    - If running a script: use the script's stem (without extension).
    - If running in a notebook/REPL: fallback to 'notebook_session'.
    """
    script_name = "notebook_session"
    try:
        main_mod = sys.modules.get("__main__")
        if main_mod is not None and hasattr(main_mod, "__file__") and main_mod.__file__:
            script_name = Path(main_mod.__file__).stem
        else:
            # Try to detect from the call stack (first .py file we find)
            for frame in inspect.stack():
                fname = frame.filename
                if fname and fname.endswith(".py"):
                    script_name = Path(fname).stem
                    break
    except Exception:
        pass
    return Path.cwd() / "outputs" / "vis" / script_name


def save_figure(
    fig,
    filename: str,
    output_dir: str | None = None,
    prefer: str = "png",
    width: int = 1400,
    height: int = 900,
    dpi: int = 150,
) -> str:
    """
    Универсальное сохранение фигур Plotly/Matplotlib.

    Поведение:
    - Plotly: prefer='png' → попытка PNG (kaleido), иначе HTML (fallback). prefer='html' → HTML.
    - Matplotlib: PNG.

    Args:
        fig: Фигура Plotly или Matplotlib
        filename: Имя файла без расширения
        output_dir: Директория для сохранения
        prefer: 'html' или 'png' (для Plotly)
        width: Ширина PNG (Plotly)
        height: Высота PNG (Plotly)
        dpi: DPI для Matplotlib PNG

    Returns:
        Абсолютный путь к сохранённому файлу
    """
    out = Path(output_dir) if output_dir else _resolve_default_output_dir()
    out.mkdir(parents=True, exist_ok=True)

    # Plotly figure detection by capability
    if hasattr(fig, "write_html"):
        if prefer.lower() == "png" and hasattr(fig, "write_image"):
            try:
                path = out / f"{filename}.png"
                # Use figure's own width/height from layout if available, otherwise use provided defaults
                fig_width = fig.layout.width if fig.layout.width else width
                fig_height = fig.layout.height if fig.layout.height else height
                fig.write_image(str(path), width=fig_width, height=fig_height)
                return str(path.resolve())
            except Exception:
                path = out / f"{filename}.html"
                fig.write_html(str(path))
                return str(path.resolve())
        else:
            path = out / f"{filename}.html"
            fig.write_html(str(path))
            return str(path.resolve())

    # Matplotlib figure
    if hasattr(fig, "savefig"):
        path = out / f"{filename}.png"
        fig.savefig(str(path), dpi=dpi, bbox_inches="tight")
        return str(path.resolve())

    raise TypeError(f"Unsupported figure type: {type(fig)}")


