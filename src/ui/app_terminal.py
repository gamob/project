#!/usr/bin/env python3
"""
Terminal-based Corporate Brain v1.0
A terminal UI version of the RAG chatbot using Rich library
"""

import os
import sys
import warnings
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
from unittest.mock import MagicMock

# Suppress Streamlit warnings (inherited from dependencies on Linux servers)
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"

mock_st = MagicMock()
sys.modules["streamlit"] = mock_st
sys.modules["streamlit.runtime"] = MagicMock()
sys.modules["streamlit.runtime.scriptrunner"] = MagicMock()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.layout import Layout
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
import time

# --- APP IMPORTS ---
from ..core.brain_service import Brain
from ..core.generate import answer_question, check_ollama_health, generate_search_queries
from ..storage.chat_store import (
    init_db, create_session, save_message,
    load_session_messages, get_all_sessions, delete_session, rename_session
)

# --- INITIALIZE ---
console = Console()
init_db()


class TerminalBrain:
    """Terminal-based Brain RAG Application"""
    
    def __init__(self):
        self.console = console
        self.brain = None
        self.session_id = None
        self.messages = []
        self.running = True
        self._initialize_brain()
    
    def _initialize_brain(self):
        """Initialize the Brain service"""
        self.console.clear()
        self._print_header()
        
        # Check Ollama health
        self.console.print("[yellow]⏳ Checking Ollama connection...[/yellow]")
        is_healthy, health_msg = check_ollama_health()
        
        if not is_healthy:
            self.console.print(f"[red]✗ Ollama Issue: {health_msg}[/red]")
            self.console.print("[red]Please start Ollama and try again.[/red]")
            sys.exit(1)
        
        self.console.print("[green]✓ Ollama Connected[/green]\n")
        
        # Initialize Brain
        self.console.print("[yellow]⏳ Initializing Brain service...[/yellow]")
        self.brain = Brain()
        
        if self.brain.is_built():
            try:
                with self.console.status("[bold cyan]Loading Brain indices...", spinner="dots"):
                    self.brain.load()
                self.console.print("[green]✓ Brain Connected! (FAISS + BM25)[/green]\n")
            except Exception as e:
                self.console.print(f"[red]✗ Failed to load brain: {e}[/red]")
                self.console.print("[yellow]⚠ Try 'Sync Brain' from main menu[/yellow]\n")
        else:
            self.console.print("[yellow]⚠ No brain found. Upload documents to get started![/yellow]\n")
    
    def _print_header(self):
        """Print the application header"""
        header_text = Text.assemble(
            ("🦖 ", "bold red"),
            ("Corporate Brain v1.0", "bold cyan")
        )
        subtitle = Text("Local • Secure • Air-gapped AI Assistant", style="dim white")
        
        self.console.print(Panel(
            header_text + "\n" + subtitle,
            border_style="cyan",
            expand=False
        ))
    
    def _print_status_bar(self):
        """Print status bar with brain status"""
        status = "[green]✓ Ready[/green]" if self.brain.is_built() else "[yellow]⚠ No documents loaded[/yellow]"
        if self.session_id:
            self.console.print(f"[dim]{status} | Session Active[/dim]")
        else:
            self.console.print(f"[dim]{status}[/dim]")
    
    def show_main_menu(self):
        """Display main menu"""
        self.console.clear()
        self._print_header()
        self._print_status_bar()
        self.console.print()
        
        menu_items = [
            ("1", "💬 Chat"),
            ("2", "📂 Manage Documents"),
            ("3", "🔄 Sync Brain"),
            ("4", "☢️  Nuke & Rebuild"),
            ("5", "📝 Chat Sessions"),
            ("6", "❌ Exit"),
        ]
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Action", style="white")
        
        for key, action in menu_items:
            table.add_row(key, action)
        
        self.console.print(table)
        self.console.print()
        
        choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3", "4", "5", "6"])
        return choice
    
    def chat_mode(self):
        """Enter chat mode"""
        if not self.brain.is_built():
            self.console.print("[red]✗ No brain available![/red]")
            self.console.print("[yellow]Please upload documents and sync the brain first.[/yellow]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")
            return
        
        self.console.clear()
        self._print_header()
        self.console.print("[cyan]Chat Mode[/cyan] - Type 'exit' or 'quit' to return to menu\n")
        
        # Load existing session or create new
        if not self.session_id:
            self.session_id = None  # Will be created on first message
        
        # Show conversation history
        if self.messages:
            self.console.print("[dim]--- Conversation History ---[/dim]")
            for msg in self.messages:
                if msg["role"] == "user":
                    self.console.print(f"\n[cyan]You:[/cyan]\n{msg['content']}")
                else:
                    self.console.print(f"\n[magenta]Brain:[/magenta]\n{msg['content']}")
            self.console.print("\n[dim]--- New Messages ---[/dim]\n")
        else:
            self.console.print("[magenta]Brain:[/magenta]")
            self.console.print("Hello! I'm your Corporate Brain. I've loaded your documents and I'm ready to help.")
            self.console.print("What's on your mind? (✧ω✧)\n")
        
        while True:
            try:
                user_input = Prompt.ask("[cyan]You[/cyan]")
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                
                if not user_input.strip():
                    continue
                
                # Create session on first message
                if not self.session_id:
                    self.session_id = create_session(user_input)
                
                # Save user message
                save_message(self.session_id, "user", user_input)
                self.messages.append({"role": "user", "content": user_input})
                self.console.print(f"\n[cyan]You:[/cyan]\n{user_input}\n")
                
                # Process with Brain
                self.console.print("[magenta]Brain:[/magenta]")
                response = self._process_question(user_input)
                
                # Save assistant message
                save_message(self.session_id, "assistant", response)
                self.messages.append({"role": "assistant", "content": response})
                self.console.print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _process_question(self, prompt: str) -> str:
        """Process user question with brain and LLM"""
        response_text = ""
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                # Generate search queries
                task_id = progress.add_task("Refining search query...", total=None)
                rewritten_query, query_variations = generate_search_queries(prompt)
                progress.stop()
                
                # Search in brain
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True
                )
                with progress:
                    task_id = progress.add_task("Checking the library...", total=None)
                    docs, low_confidence, confidence_pct = self.brain.search(
                        rewritten_query,
                        extra_queries=query_variations
                    )
                
                # Generate response
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True
                )
                with progress:
                    task_id = progress.add_task("Consulting the Llama...", total=None)
                    response_gen, sources = answer_question(
                        prompt,
                        docs,
                        stream=True
                    )
                
                # Collect streamed response
                for chunk in response_gen:
                    response_text += chunk
                    self.console.print(chunk, end="", highlight=False)
                    self.console.file.flush()
                
                self.console.print()  # Newline after response
                
                # Show sources and confidence
                self._show_sources(sources, confidence_pct)
                
        except Exception as e:
            self.console.print(f"[red]Error processing question: {e}[/red]")
        
        return response_text
    
    def _show_sources(self, sources: List[str], confidence_pct: int):
        """Display sources and confidence score"""
        self.console.print()
        
        # Confidence indicator
        if confidence_pct >= 70:
            conf_color, conf_label = "green", "🟢 High"
        elif confidence_pct >= 40:
            conf_color, conf_label = "yellow", "🟡 Medium"
        else:
            conf_color, conf_label = "red", "🔴 Low"
        
        conf_text = f"Retrieval Confidence: [{conf_color}]{conf_label}[/{conf_color}] — {confidence_pct}%"
        self.console.print(f"[dim]{conf_text}[/dim]")
        
        # Progress bar
        filled = int(20 * confidence_pct / 100)
        bar = "█" * filled + "░" * (20 - filled)
        self.console.print(f"[dim][{conf_color}]{bar}[/{conf_color}][/dim]")
        
        if confidence_pct < 40:
            self.console.print("[yellow]⚠ The documents may not cover this topic well.[/yellow]")
        
        # Sources
        if sources:
            self.console.print("\n[cyan]📚 References:[/cyan]")
            for i, source in enumerate(sources, 1):
                self.console.print(f"[dim]{i}. 📄 {source}[/dim]")
    
    def manage_documents(self):
        """Document management interface"""
        self.console.clear()
        self._print_header()
        self.console.print("[cyan]Document Management[/cyan]\n")
        
        while True:
            # List documents
            if os.path.exists("data") and os.listdir("data"):
                files = sorted(os.listdir("data"))
                
                table = Table(title="📂 Uploaded Documents", box=box.ROUNDED)
                table.add_column("File", style="cyan")
                table.add_column("Size", style="white")
                
                for filename in files:
                    filepath = os.path.join("data", filename)
                    size = os.path.getsize(filepath)
                    size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
                    table.add_row(filename, size_str)
                
                self.console.print(table)
                self.console.print()
            else:
                self.console.print("[yellow]No documents uploaded yet.[/yellow]\n")
            
            # Menu
            menu_items = [
                ("1", "📥 Upload new document"),
                ("2", "🗑️  Delete document"),
                ("3", "◀️  Back to menu"),
            ]
            
            table = Table(show_header=False, box=box.ROUNDED)
            table.add_column("Option", style="cyan")
            table.add_column("Action", style="white")
            
            for key, action in menu_items:
                table.add_row(key, action)
            
            self.console.print(table)
            self.console.print()
            
            choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3"])
            
            if choice == "1":
                self._upload_document()
            elif choice == "2":
                self._delete_document()
            elif choice == "3":
                break
            
            self.console.clear()
            self._print_header()
            self.console.print("[cyan]Document Management[/cyan]\n")
    
    def _upload_document(self):
        """Upload a document"""
        self.console.print("\n[cyan]Upload Document[/cyan]")
        self.console.print("[dim]Enter the full file path to the document:[/dim]")
        
        file_path = Prompt.ask("[cyan]File path[/cyan]")
        
        if not os.path.exists(file_path):
            self.console.print(f"[red]✗ File not found: {file_path}[/red]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")
            return
        
        os.makedirs("data", exist_ok=True)
        filename = os.path.basename(file_path)
        dest_path = os.path.join("data", filename)
        
        try:
            with open(file_path, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
            self.console.print(f"[green]✓ Uploaded: {filename}[/green]")
            self.console.print("[yellow]⚠ Don't forget to 'Sync Brain' to reindex![/yellow]")
        except Exception as e:
            self.console.print(f"[red]✗ Upload failed: {e}[/red]")
        
        Prompt.ask("[dim]Press Enter to continue[/dim]")
    
    def _delete_document(self):
        """Delete a document"""
        if not os.path.exists("data") or not os.listdir("data"):
            self.console.print("[yellow]No documents to delete.[/yellow]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")
            return
        
        files = sorted(os.listdir("data"))
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("File", style="white")
        
        for i, filename in enumerate(files, 1):
            table.add_row(str(i), filename)
        
        self.console.print("\n[cyan]Select document to delete:[/cyan]")
        self.console.print(table)
        self.console.print()
        
        choice = Prompt.ask("[cyan]Enter number[/cyan]", choices=[str(i) for i in range(1, len(files) + 1)])
        filename = files[int(choice) - 1]
        
        if Confirm.ask(f"[yellow]Delete {filename}?[/yellow]"):
            os.remove(os.path.join("data", filename))
            self.console.print(f"[green]✓ Deleted {filename}[/green]")
            self.console.print("[yellow]⚠ Click 'Sync Brain' to reindex![/yellow]")
        
        Prompt.ask("[dim]Press Enter to continue[/dim]")
    
    def sync_brain(self):
        """Sync brain indices"""
        if not os.path.exists("data") or not os.listdir("data"):
            self.console.print("[red]✗ No documents found in data folder![/red]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")
            return
        
        self.console.clear()
        self._print_header()
        self.console.print("[cyan]Syncing Brain[/cyan]\n")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task_id = progress.add_task("Syncing brain indices...", total=None)
                self.brain.sync_indices()
            
            self.console.print("[green]✓ Brain synced successfully![/green]")
        except Exception as e:
            self.console.print(f"[red]✗ Sync failed: {e}[/red]")
        
        Prompt.ask("[dim]Press Enter to continue[/dim]")
    
    def nuke_and_rebuild(self):
        """Nuke and rebuild brain"""
        self.console.clear()
        self._print_header()
        self.console.print("[cyan]Nuke & Rebuild[/cyan]\n")
        self.console.print("[red]⚠️  This will delete ALL indices and rebuild from scratch![/red]\n")
        
        if not Confirm.ask("[red]Are you sure?[/red]"):
            return
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task_id = progress.add_task("Wiping old indices and building fresh...", total=None)
                self.brain.build()
            
            self.console.print("[green]✓ Brain rebuilt from zero![/green]")
        except Exception as e:
            self.console.print(f"[red]✗ Rebuild failed: {e}[/red]")
        
        Prompt.ask("[dim]Press Enter to continue[/dim]")
    
    def manage_sessions(self):
        """Chat sessions management"""
        self.console.clear()
        self._print_header()
        self.console.print("[cyan]Chat Sessions[/cyan]\n")
        
        sessions = get_all_sessions()
        
        if not sessions:
            self.console.print("[yellow]No chat sessions yet.[/yellow]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")
            return
        
        while True:
            # Build menu
            choices = []
            table = Table(title="📝 Previous Chats", box=box.ROUNDED)
            table.add_column("Option", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Date", style="dim")
            
            sessions = get_all_sessions()  # Refresh
            for i, session in enumerate(sessions, 1):
                table.add_row(
                    str(i),
                    session["title"],
                    session.get("created_at", "Unknown")
                )
                choices.append(str(i))
            
            choices.append(str(len(sessions) + 1))
            
            self.console.print(table)
            self.console.print()
            
            menu_items = [(str(i+1), "Load") for i in range(len(sessions))]
            menu_items.append((str(len(sessions) + 1), "Back"))
            
            choice = Prompt.ask("[cyan]Select session or back[/cyan]", choices=choices)
            
            if choice == str(len(sessions) + 1):
                break
            
            session_idx = int(choice) - 1
            session = sessions[session_idx]
            
            self.console.print()
            action_menu = [
                ("1", "Load"),
                ("2", "Rename"),
                ("3", "Delete"),
                ("4", "Back"),
            ]
            
            table = Table(show_header=False, box=box.ROUNDED)
            table.add_column("Option", style="cyan")
            table.add_column("Action", style="white")
            
            for key, action in action_menu:
                table.add_row(key, action)
            
            self.console.print(table)
            self.console.print()
            
            action = Prompt.ask("[cyan]Select action[/cyan]", choices=["1", "2", "3", "4"])
            
            if action == "1":
                self.session_id = session["id"]
                self.messages = load_session_messages(session["id"])
                self.console.print(f"[green]✓ Loaded: {session['title']}[/green]")
                Prompt.ask("[dim]Press Enter to continue[/dim]")
                return
            
            elif action == "2":
                new_title = Prompt.ask("[cyan]New title[/cyan]")
                if new_title.strip():
                    rename_session(session["id"], new_title)
                    self.console.print(f"[green]✓ Renamed to: {new_title}[/green]")
            
            elif action == "3":
                if Confirm.ask(f"[red]Delete '{session['title']}'?[/red]"):
                    delete_session(session["id"])
                    if self.session_id == session["id"]:
                        self.session_id = None
                        self.messages = []
                    self.console.print("[green]✓ Deleted[/green]")
            
            self.console.clear()
            self._print_header()
            self.console.print("[cyan]Chat Sessions[/cyan]\n")
    
    def run(self):
        """Main application loop"""
        while self.running:
            choice = self.show_main_menu()
            
            if choice == "1":
                self.chat_mode()
            elif choice == "2":
                self.manage_documents()
            elif choice == "3":
                self.sync_brain()
            elif choice == "4":
                self.nuke_and_rebuild()
            elif choice == "5":
                self.manage_sessions()
            elif choice == "6":
                self.console.print("[cyan]Goodbye! 👋[/cyan]")
                self.running = False
        
        sys.exit(0)


def main():
    """Entry point"""
    try:
        app = TerminalBrain()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
