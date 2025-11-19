"""Console UI components using Rich."""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_intro():
    """Display intro banner."""
    console.clear()
    console.print("\n🤖 [bold cyan]AUTONOMOUS AGENT WITH HYBRID MEMORY[/bold cyan]\n")
    console.print("=" * 80, style="green")
    console.print()


def print_result(text: str, theme: str = "hacker"):
    """Display result in themed panel."""
    THEMES = {
        "hacker": ("👾 RESULT 👾", "green"),
        "matrix": ("⟡ MATRIX ⟡", "cyan"),
        "fire": ("🔥 OUTPUT 🔥", "red"),
        "minimal": ("RESULT", "white"),
    }
    title, color = THEMES.get(theme, THEMES["minimal"])
    panel = Panel(Text(text, style=color), title=title, border_style=color)
    console.print(panel)


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓ {message}[/green]")


def print_warning(message: str):
    """Print warning message."""
