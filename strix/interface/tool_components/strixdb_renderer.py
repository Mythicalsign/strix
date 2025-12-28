"""
StrixDB Renderer - Rich TUI rendering for StrixDB operations.
"""

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .base_renderer import BaseRenderer


class StrixDBSaveRenderer(BaseRenderer):
    """Renderer for strixdb_save results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render save operation result."""
        console = console or Console()

        if result.get("success"):
            item = result.get("item", {})
            
            content = Text()
            content.append("✅ ", style="bold green")
            content.append("Saved to StrixDB\n\n", style="bold green")
            content.append("Name: ", style="dim")
            content.append(f"{item.get('name', 'unknown')}\n", style="bold white")
            content.append("Category: ", style="dim")
            content.append(f"{item.get('category', 'unknown')}\n", style="bold cyan")
            content.append("Path: ", style="dim")
            content.append(f"{item.get('path', 'unknown')}\n", style="white")
            
            if item.get("tags"):
                content.append("Tags: ", style="dim")
                content.append(", ".join(item["tags"]), style="bold yellow")

            panel = Panel(
                content,
                title="[bold green]📦 StrixDB Save",
                border_style="green",
            )
            console.print(panel)
        else:
            error = result.get("error", "Unknown error")
            content = Text()
            content.append("❌ ", style="bold red")
            content.append("Save Failed\n\n", style="bold red")
            content.append(error, style="red")

            panel = Panel(
                content,
                title="[bold red]📦 StrixDB Error",
                border_style="red",
            )
            console.print(panel)


class StrixDBSearchRenderer(BaseRenderer):
    """Renderer for strixdb_search results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render search results."""
        console = console or Console()

        if result.get("success"):
            results = result.get("results", [])
            total = result.get("total_count", len(results))
            query = result.get("query", "")

            if not results:
                content = Text()
                content.append("🔍 ", style="bold yellow")
                content.append(f"No results found for: ", style="white")
                content.append(query, style="bold yellow")

                panel = Panel(
                    content,
                    title="[bold yellow]📦 StrixDB Search",
                    border_style="yellow",
                )
                console.print(panel)
                return

            table = Table(
                title=f"Search Results ({len(results)} of {total})",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="white")
            table.add_column("Category", style="cyan")
            table.add_column("Path", style="dim")

            for item in results:
                table.add_row(
                    item.get("name", "unknown"),
                    item.get("category", "unknown"),
                    item.get("path", ""),
                )

            panel = Panel(
                table,
                title=f"[bold cyan]🔍 StrixDB Search: {query}",
                border_style="cyan",
            )
            console.print(panel)
        else:
            error = result.get("error", "Search failed")
            console.print(f"[red]❌ Search Error: {error}[/red]")


class StrixDBGetRenderer(BaseRenderer):
    """Renderer for strixdb_get results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render get result."""
        console = console or Console()

        if result.get("success"):
            item = result.get("item", {})
            metadata = item.get("metadata", {})

            content = Text()
            content.append("📄 ", style="bold blue")
            content.append(f"{item.get('name', 'unknown')}\n\n", style="bold white")
            
            content.append("Category: ", style="dim")
            content.append(f"{item.get('category', 'unknown')}\n", style="cyan")
            
            if metadata.get("description"):
                content.append("Description: ", style="dim")
                content.append(f"{metadata['description']}\n", style="white")
            
            if metadata.get("tags"):
                content.append("Tags: ", style="dim")
                content.append(f"{', '.join(metadata['tags'])}\n", style="yellow")
            
            content.append("\n--- Content ---\n", style="dim")
            
            item_content = item.get("content", "")
            if len(item_content) > 2000:
                content.append(f"{item_content[:2000]}...\n", style="white")
                content.append(f"(truncated, total {len(item_content)} characters)", style="dim")
            else:
                content.append(item_content, style="white")

            panel = Panel(
                content,
                title="[bold blue]📦 StrixDB Item",
                border_style="blue",
            )
            console.print(panel)
        else:
            error = result.get("error", "Item not found")
            console.print(f"[red]❌ Get Error: {error}[/red]")


class StrixDBListRenderer(BaseRenderer):
    """Renderer for strixdb_list results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render list results."""
        console = console or Console()

        if result.get("success"):
            items = result.get("items", [])
            total = result.get("total", len(items))

            if not items:
                console.print("[yellow]📦 StrixDB is empty[/yellow]")
                return

            # Group by category
            by_category: dict[str, list[dict[str, Any]]] = {}
            for item in items:
                cat = item.get("category", "unknown")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(item)

            tree = Tree("📦 [bold]StrixDB Contents[/bold]")

            for category, cat_items in sorted(by_category.items()):
                branch = tree.add(f"📁 [cyan]{category}[/cyan] ({len(cat_items)} items)")
                for item in cat_items[:10]:  # Show max 10 per category
                    branch.add(f"📄 [white]{item.get('name', 'unknown')}[/white]")
                if len(cat_items) > 10:
                    branch.add(f"[dim]... and {len(cat_items) - 10} more[/dim]")

            panel = Panel(
                tree,
                title=f"[bold cyan]📦 StrixDB ({total} items)",
                border_style="cyan",
            )
            console.print(panel)
        else:
            error = result.get("error", "List failed")
            console.print(f"[red]❌ List Error: {error}[/red]")


class StrixDBDeleteRenderer(BaseRenderer):
    """Renderer for strixdb_delete results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render delete result."""
        console = console or Console()

        if result.get("success"):
            message = result.get("message", "Item deleted")
            console.print(f"[green]🗑️ {message}[/green]")
        else:
            error = result.get("error", "Delete failed")
            console.print(f"[red]❌ Delete Error: {error}[/red]")


class StrixDBCategoriesRenderer(BaseRenderer):
    """Renderer for strixdb_get_categories results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render categories."""
        console = console or Console()

        if result.get("success"):
            categories = result.get("categories", [])

            table = Table(
                title="StrixDB Categories",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Category", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Items", style="yellow", justify="right")

            for cat in categories:
                table.add_row(
                    cat.get("name", ""),
                    cat.get("description", ""),
                    str(cat.get("item_count", 0)),
                )

            panel = Panel(
                table,
                title="[bold cyan]📁 StrixDB Categories",
                border_style="cyan",
            )
            console.print(panel)
        else:
            error = result.get("error", "Failed to get categories")
            console.print(f"[red]❌ Error: {error}[/red]")


class StrixDBStatsRenderer(BaseRenderer):
    """Renderer for strixdb_get_stats results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render stats."""
        console = console or Console()

        if result.get("success"):
            stats = result.get("stats", {})

            content = Text()
            content.append("📊 StrixDB Statistics\n\n", style="bold cyan")
            
            content.append("Repository: ", style="dim")
            content.append(f"{stats.get('repo_name', 'unknown')}\n", style="white")
            
            content.append("Branch: ", style="dim")
            content.append(f"{stats.get('branch', 'main')}\n", style="white")
            
            content.append("Total Items: ", style="dim")
            content.append(f"{stats.get('total_items', 0)}\n", style="bold green")
            
            content.append("Size: ", style="dim")
            content.append(f"{stats.get('size_kb', 0)} KB\n", style="white")
            
            content.append("Visibility: ", style="dim")
            content.append(f"{stats.get('visibility', 'unknown')}\n", style="white")
            
            if stats.get("last_updated"):
                content.append("Last Updated: ", style="dim")
                content.append(f"{stats['last_updated']}\n", style="white")
            
            content.append("\n📁 Items by Category:\n", style="bold")
            categories = stats.get("categories", {})
            for cat, count in sorted(categories.items()):
                if count > 0:
                    content.append(f"  {cat}: ", style="dim")
                    content.append(f"{count}\n", style="cyan")

            panel = Panel(
                content,
                title="[bold cyan]📦 StrixDB Stats",
                border_style="cyan",
            )
            console.print(panel)
        else:
            error = result.get("error", "Failed to get stats")
            console.print(f"[red]❌ Stats Error: {error}[/red]")


class StrixDBRecentRenderer(BaseRenderer):
    """Renderer for strixdb_get_recent results."""

    def render(self, result: dict[str, Any], console: Console | None = None) -> None:
        """Render recent items."""
        console = console or Console()

        if result.get("success"):
            items = result.get("items", [])

            if not items:
                console.print("[yellow]📦 No recent items found[/yellow]")
                return

            table = Table(
                title="Recent StrixDB Activity",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="white")
            table.add_column("Category", style="cyan")
            table.add_column("Action", style="yellow")
            table.add_column("Time", style="dim")

            for item in items:
                action = item.get("action", "unknown")
                action_style = "green" if action == "added" else "yellow"
                
                table.add_row(
                    item.get("name", "unknown"),
                    item.get("category", "unknown"),
                    f"[{action_style}]{action}[/{action_style}]",
                    item.get("timestamp", "")[:10] if item.get("timestamp") else "",
                )

            panel = Panel(
                table,
                title="[bold cyan]🕒 Recent StrixDB Activity",
                border_style="cyan",
            )
            console.print(panel)
        else:
            error = result.get("error", "Failed to get recent items")
            console.print(f"[red]❌ Error: {error}[/red]")


# Mapping of tool names to renderers
STRIXDB_RENDERERS = {
    "strixdb_save": StrixDBSaveRenderer,
    "strixdb_search": StrixDBSearchRenderer,
    "strixdb_get": StrixDBGetRenderer,
    "strixdb_list": StrixDBListRenderer,
    "strixdb_update": StrixDBSaveRenderer,  # Same as save
    "strixdb_delete": StrixDBDeleteRenderer,
    "strixdb_get_categories": StrixDBCategoriesRenderer,
    "strixdb_get_stats": StrixDBStatsRenderer,
    "strixdb_get_recent": StrixDBRecentRenderer,
}


def get_strixdb_renderer(tool_name: str) -> type[BaseRenderer] | None:
    """Get the appropriate renderer for a StrixDB tool."""
    return STRIXDB_RENDERERS.get(tool_name)
