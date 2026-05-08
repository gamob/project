# Terminal UI Preview

This document shows what the app_terminal.py looks like when running.

## Main Menu

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
├─────────────────────────────────────────┤
│ Assistant                               │
│ [Ready]                                 │
╰─────────────────────────────────────────╯

┌─────────────────────────────────────────┐
│ Option │ Action                          │
├────────┼─────────────────────────────────┤
│ 1      │ 💬 Chat                         │
│ 2      │ 📂 Manage Documents            │
│ 3      │ 🔄 Sync Brain                  │
│ 4      │ ☢️  Nuke & Rebuild             │
│ 5      │ 📝 Chat Sessions               │
│ 6      │ ❌ Exit                         │
└────────┴─────────────────────────────────┘

Select option: _
```

## Chat Mode

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Chat Mode - Type 'exit' or 'quit' to return to menu

Brain:
Hello! I'm your Corporate Brain. I've loaded your documents 
and I'm ready to help. What's on your mind? (✧ω✧)

You:
What does the document say about project timeline?

⠙ Consulting the Llama...

Brain:
The project timeline mentions three key phases: Phase 1 spans 
Q1-Q2 with planning and design, Phase 2 covers Q3-Q4 for 
development, and Phase 3 in Q1 next year focuses on launch 
and optimization.

Retrieval Confidence: 🟢 High — 87%
████████████████████░░░░░░░░░░░░

📚 References:
1. 📄 Project Charter (Page 2)
2. 📄 Timeline.pdf (Page 1)

You:
_
```

## Document Management

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Document Management

╭─ 📂 Uploaded Documents ──────────────────╮
│ File                  │ Size             │
├───────────────────────┼──────────────────┤
│ Project_Charter.pdf   │ 2.3 MB           │
│ Timeline.md          │ 0.5 KB           │
│ Requirements.docx    │ 1.1 MB           │
│ Budget.xlsx          │ 0.8 MB           │
╰───────────────────────┴──────────────────╯

┌────────────────────────────────────┐
│ Option │ Action                    │
├────────┼───────────────────────────┤
│ 1      │ 📥 Upload new document    │
│ 2      │ 🗑️  Delete document      │
│ 3      │ ◀️  Back to menu          │
└────────┴───────────────────────────┘

Select option: _
```

## Brain Sync Progress

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Syncing Brain

⠴ Syncing brain indices...
  Processing: 4/4 documents
  Building FAISS index... [████████████████░░] 80%
  
  ✓ Brain synced successfully!

Press Enter to continue: _
```

## Chat Sessions

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Chat Sessions

╭─ 📝 Previous Chats ──────────────────────╮
│ Option │ Title              │ Date       │
├────────┼────────────────────┼────────────┤
│ 1      │ Q3 Budget Review   │ 2024-03-15 │
│ 2      │ Project Timeline   │ 2024-03-14 │
│ 3      │ Team Updates       │ 2024-03-12 │
╰────────┴────────────────────┴────────────╯

Select session or back: _
```

## Session Actions Menu

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Chat Sessions

[Session: Q3 Budget Review]

┌─────────────────────────────────────────┐
│ Option │ Action                          │
├────────┼─────────────────────────────────┤
│ 1      │ Load                            │
│ 2      │ Rename                          │
│ 3      │ Delete                          │
│ 4      │ Back                            │
└────────┴─────────────────────────────────┘

Select action: _
```

## Rebuild Confirmation

```
╭─────────────────────────────────────────╮
│ 🦖 Corporate Brain v1.0                 │
│ Local • Secure • Air-gapped AI          │
╰─────────────────────────────────────────╯

Nuke & Rebuild

⚠️  This will delete ALL indices and rebuild from scratch!

Are you sure? [y/N]: _
```

## Status Messages

### Success
```
[green]✓ Uploaded: ProjectCharter.pdf[/green]
[yellow]⚠ Don't forget to 'Sync Brain' to reindex![/yellow]
```

### Error
```
[red]✗ File not found: C:\Documents\Missing.pdf[/red]
```

### Processing
```
⠙ Refining search query...
⠹ Checking the library...
⠸ Consulting the Llama...
[green]✓ Done![/green]
```

### Confidence Levels
```
🟢 High — 87%     [████████████████░░░░░░░░░░░░░░] 
🟡 Medium — 52%   [██████████░░░░░░░░░░░░░░░░░░░░░]
🔴 Low — 28%      [██████░░░░░░░░░░░░░░░░░░░░░░░░░]
```

## Color Scheme

- **Cyan** (`[cyan]...[/cyan]`) - Headers, options, prompts
- **Yellow** (`[yellow]...[/yellow]`) - Warnings, important notices
- **Red** (`[red]...[/red]`) - Errors, critical messages
- **Green** (`[green]...[/green]`) - Success messages
- **Magenta** (`[magenta]...[/magenta]`) - Assistant responses
- **White** - Regular text
- **Dim** (`[dim]...[/dim]`) - Secondary information

## Interactive Elements

- **Tables** with automatic formatting
- **Panels** for section organization
- **Progress bars** for long operations
- **Spinners** for loading states
- **Prompts** for user input with validation
- **Confirmations** with y/N options

## Keyboard Navigation

- **Arrow Keys** - Not used (simplified for compatibility)
- **Numbers** - Select options (1-6)
- **Enter** - Confirm selections
- **Type** - Chat messages and text input
- **exit/quit** - Leave chat mode
- **Ctrl+C** - Force exit (any mode)

## Responsive Design

The UI automatically adapts to terminal width:
- Narrow terminals: Tables collapse to essentials
- Wide terminals: Full table formatting
- Mobile SSH: Minimal columns

---

**This is what you'll see when you run `python app_terminal.py`!**

All styling uses the Rich library's built-in color and formatting system.
