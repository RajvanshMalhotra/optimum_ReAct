"""Console UI components using Rich."""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_intro():
    """Display intro banner."""
    console.clear()
    console.print("\n🤖 [bold cyan]AUTONOMOUS AGENT WITH HYBRID MEMORY[/bold cyan]\n")
