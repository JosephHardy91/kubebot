# KubeBot TUI

A terminal UI for interacting with the KubeBot backend. Displays answers in a main pane with a source reference pane on the right.

## Layout

- **Left pane (75%)** — Q&A history. Shows your query and KubeBot's answer.
- **Right pane (24%)** — Source references for the selected answer. Click a source to view its content.

## Keybindings

| Key    | Action                             |
| ------ | ---------------------------------- |
| `Up`   | Previous Q&A in history            |
| `Down` | Next Q&A in history                |
| `Left` | Refresh panes (return from source) |

## Requirements

```
pip install textual httpx
```

## Usage

Start the backend first (`bash backend/dev.sh`), then:

```
python interfaces/tui/kubebot_tui.py
```

Or use the alias (see `interfaces/make_local_alias.sh`):

```
kubebot
```

Type a question in the input bar and press Enter. Navigate answer history with arrow keys. Click sources in the right pane to inspect them.
