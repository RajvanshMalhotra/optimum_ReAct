# """Console UI components using Rich."""
# from rich.console import Console
# from rich.panel import Panel
# from rich.text import Text

# console = Console()


# def print_intro():
#     """Display intro banner."""
#     console.clear()
#     console.print("\n🤖 [bold cyan]AUTONOMOUS AGENT WITH HYBRID MEMORY[/bold cyan]\n")
#     console.print("=" * 80, style="green")
#     console.print()


# def print_result(text: str, theme: str = "hacker"):
#     """Display result in themed panel."""
#     THEMES = {
#         "hacker": ("👾 RESULT 👾", "green"),
#         "matrix": ("⟡ MATRIX ⟡", "cyan"),
#         "fire": ("🔥 OUTPUT 🔥", "red"),
#         "minimal": ("RESULT", "white"),
#     }
#     title, color = THEMES.get(theme, THEMES["minimal"])
#     panel = Panel(Text(text, style=color), title=title, border_style=color)
#     console.print(panel)


# def print_success(message: str):
#     """Print success message."""
#     console.print(f"[green]✓ {message}[/green]")


# def print_warning(message: str):
#     """Print warning message."""
#     console.print(f"[yellow]⚠ {message}[/yellow]")


# def print_error(message: str):
#     """Print error message."""
#     console.print(f"[red]✗ {message}[/red]")


# def print_info(message: str):
#     """Print info message."""
#     console.print(f"[cyan]ℹ {message}[/cyan]")


# def print_dim(message: str):
#     """Print dimmed message."""
#     console.print(f"[dim]{message}[/dim]")


# def get_input(prompt: str, default: str = "") -> str:
#     """Get user input with prompt."""
#     value = console.input(f"[bold]{prompt}[/bold] ")
#     return value.strip() or default
"""Console UI components using Rich."""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

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
    console.print(f"[yellow]⚠ {message}[/yellow]")


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗ {message}[/red]")


def print_info(message: str):
    """Print info message."""
    console.print(f"[cyan]ℹ {message}[/cyan]")


def print_dim(message: str):
    """Print dimmed message."""
    console.print(f"[dim]{message}[/dim]")


def get_input(prompt: str, default: str = "") -> str:
    """Get user input with prompt."""
    value = console.input(f"[bold]{prompt}[/bold] ")
    return value.strip() or default


def print_table(data: list, headers: list, title: str = None):
    """Print data in a formatted table."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add columns
    for header in headers:
        table.add_column(header)
    
    # Add rows
    for row in data:
        table.add_row(*[str(cell) for cell in row])
    
    console.print(table)


def print_memory_summary(stats: dict):
    """Print memory statistics in a nice format."""
    console.print("\n[bold cyan]Memory Summary[/bold cyan]")
    console.print("─" * 50)
    
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Session ID", stats.get('session_id', 'N/A'))
    table.add_row("Memories in RAM", str(stats.get('graph', {}).get('total_nodes', 0)))
    table.add_row("Memories in DB", str(stats.get('store', {}).get('total_memories', 0)))
    table.add_row("Total Sessions", str(stats.get('store', {}).get('total_sessions', 0)))
    table.add_row("Session Memory Count", str(stats.get('session_memory_count', 0)))
    
    console.print(table)
    console.print()


def print_agent_status(active: bool, stats: dict = None):
    """Print agent status."""
    if active:
        console.print("[green]✓ Agent Active[/green]")
        if stats:
            console.print(f"  RAM: {stats.get('graph', {}).get('total_nodes', 0)} memories")
            console.print(f"  DB: {stats.get('store', {}).get('total_memories', 0)} memories")
    else:
        console.print("[red]✗ Agent Inactive[/red]")


def print_step(step_num: int, action: str, reasoning: str = None):
    """Print agent reasoning step."""
    console.print(f"\n[cyan]💭 Step {step_num}[/cyan]")
    if reasoning:
        console.print(f"[dim]{reasoning[:100]}...[/dim]")
    console.print(f"[green]→ {action}[/green]")


def print_tool_execution(tool_name: str, query: str = None):
    """Print tool execution."""
    console.print(f"[blue]🔧 {tool_name}[/blue]")
    if query:
        console.print(f"[dim]  Query: {query[:50]}...[/dim]")


def show_progress(description: str):
    """Show a progress spinner (context manager)."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    )


def print_separator(char: str = "=", length: int = 80, color: str = "white"):
    """Print a separator line."""
    console.print(char * length, style=color)


def print_section_header(text: str, color: str = "cyan"):
    """Print a section header."""
    console.print(f"\n[bold {color}]{text}[/bold {color}]")
    console.print("─" * len(text))


def clear_screen():
    """Clear the console screen."""
    console.clear()


def print_welcome():
    """Print welcome message."""
    from rich.align import Align
    from rich.text import Text
    
    title = Text("EZAgent Framework", style="bold cyan")
    subtitle = Text("Build Intelligent AI Agents with Memory", style="dim")
    
    console.print()
    console.print(Align.center(title))
    console.print(Align.center(subtitle))
    console.print()
    print_separator()


def print_menu(options: list, title: str = "Menu"):
    """Print a menu with options."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print()
    
    for i, option in enumerate(options, 1):
        console.print(f"  [green]{i}.[/green] {option}")
    
    console.print()


def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    default_text = "Y/n" if default else "y/N"
    response = console.input(f"[yellow]{message}[/yellow] [{default_text}] ")
    
    if not response:
        return default
    
    return response.lower() in ['y', 'yes']


def print_json_pretty(data: dict, title: str = None):
    """Print JSON data in a pretty format."""
    from rich.json import JSON
    
    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
    
    console.print(JSON.from_data(data))


def print_code(code: str, language: str = "python", title: str = None):
    """Print code with syntax highlighting."""
    from rich.syntax import Syntax
    
    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
    
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def print_markdown(text: str):
    """Print markdown formatted text."""
    from rich.markdown import Markdown
    
    md = Markdown(text)
    console.print(md)


# Example usage
if __name__ == "__main__":
    # Test all functions
    print_welcome()
    
    print_section_header("Agent Status")
    print_agent_status(True, {
        'graph': {'total_nodes': 42},
        'store': {'total_memories': 150, 'total_sessions': 5}
    })
    
    print_section_header("Memory Summary")
    print_memory_summary({
        'session_id': '20241226_120000',
        'graph': {'total_nodes': 42},
        'store': {'total_memories': 150, 'total_sessions': 5},
        'session_memory_count': 10
    })
    
    print_section_header("Messages")
    print_success("Operation completed successfully")
    print_warning("This is a warning message")
    print_error("This is an error message")
    print_info("This is an info message")
    
    print_section_header("Agent Execution")
    print_step(1, "web_search", "Searching for information about AI")
    print_tool_execution("web_search", "latest AI developments")
    
    print_section_header("Data Table")
    print_table(
        data=[
            ["Memory 1", "fact", "0.9", "5"],
            ["Memory 2", "thought", "0.7", "12"],
            ["Memory 3", "preference", "0.8", "3"]
        ],
        headers=["ID", "Type", "Importance", "Connections"],
        title="Top Memories"
    )
    
    print_section_header("Menu")
    print_menu([
        "Ask a question",
        "View memories",
        "Clear session",
        "Exit"
    ], "Main Menu")
    
    print_section_header("Results")
    print_result("This is a test result with some content", theme="hacker")