# Conjurer

A terminal tool that monitors and captures chat history from AI coding assistants like Claude Code, Codex, and Trae.

## Features

- **Real-time monitoring** of AI terminal processes
- **Structured data capture** with timestamps and conversation flow
- **Multiple output formats** (JSON, TXT)
- **Configurable process detection** for different AI tools
- **Automatic session management** (start/stop detection)

## Installation

```bash
./install.sh
```

## Usage

### Basic monitoring
```bash
python3 conjurer.py
```

### Custom output directory
```bash
python3 conjurer.py --output-dir /path/to/sessions
```

### Verbose logging
```bash
python3 conjurer.py --verbose
```

## Output Structure

### JSON Format
```json
{
  "ai_type": "claude",
  "pid": 12345,
  "start_time": "2025-01-13T10:30:00",
  "end_time": "2025-01-13T11:15:00",
  "conversations": [
    {
      "timestamp": "2025-01-13T10:30:15",
      "type": "user_prompt",
      "content": "Help me create a function...",
      "ai_type": "claude"
    },
    {
      "timestamp": "2025-01-13T10:30:18",
      "type": "system_response", 
      "content": "I'll help you create that function...",
      "ai_type": "claude"
    }
  ],
  "process_info": {...},
  "raw_output": "..."
}
```

### Text Format
```
AI Session Capture - CLAUDE
==================================================
Process ID: 12345
Start Time: 2025-01-13T10:30:00
End Time: 2025-01-13T11:15:00
==================================================

[1] USER_PROMPT - 2025-01-13T10:30:15
Help me create a function...
--------------------------------------------------

[2] SYSTEM_RESPONSE - 2025-01-13T10:30:18
I'll help you create that function...
--------------------------------------------------
```

## Configuration

Edit `config.json` to customize:

- **Target processes**: Add patterns for detecting AI tools
- **Log locations**: Specify where to look for AI tool logs
- **Conversation patterns**: Define regex patterns for parsing chats
- **Output formats**: Enable/disable different output types
- **Monitoring settings**: Adjust check intervals and cleanup

## Supported AI Tools

- **Claude Code** (`claude`, `claude-code`)
- **OpenAI Codex** (`codex`, `github-copilot`) 
- **Trae** (`trae`, `trae-ai`)

## Files Generated

- `{ai_type}_session_{pid}_{timestamp}.json` - Structured session data
- `{ai_type}_session_{pid}_{timestamp}.txt` - Human-readable format
- `monitor.log` - Monitor activity log

## Requirements

- Python 3.6+
- `psutil` package
- Unix-like system (Linux/macOS)

## Security Note

This tool monitors process information and attempts to capture terminal output for defensive security analysis only. It respects system permissions and does not bypass security controls.