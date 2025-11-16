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
