# Getting Started with pyclif

## Installation

Install pyclif using pip:

```bash
pip install pyclif
```

## Requirements

- Python 3.10 or higher
- Dependencies are automatically installed

## Quick Start

Here's a minimal example:

```python
from pyclif import app_group, command, option


@app_group()
def main():
    """My CLI application."""
    pass


@main.command()
@option("--name", "-n", help="Your name")
def hello(name):
    """Say hello."""
    print(f"Hello {name}!")


if __name__ == "__main__":
    main()
```

Save this as `my_cli.py` and run it:

```bash
python my_cli.py --help
python my_cli.py hello --name "World"
python my_cli.py hello -n "Alice"
```

## Your First CLI Application

### Step 1: Create the main group

```python
from pyclif import app_group


@app_group(
    name="myapp",
    auto_envvar_prefix="MYAPP"
)
def cli():
    """My Application — a sample CLI built with pyclif."""
    pass
```

### Step 2: Add a simple command

```python
from pyclif import app_group, option


@app_group(name="myapp", auto_envvar_prefix="MYAPP")
def cli():
    """My Application."""
    pass


@cli.command()
@option("--message", "-m", default="Hello World", help="Message to display")
def hello(message):
    """Display a greeting message."""
    print(message)
```

### Step 3: Add a command group

```python
from pyclif import group, option


@group(name="database")
def database():
    """Database management commands."""
    pass


@database.command()
@option("--url", "-u", required=True, help="Database URL")
@option("--timeout", "-t", type=int, default=30, help="Connection timeout")
def connect(url, timeout):
    """Connect to the database."""
    print(f"Connecting to {url} with timeout {timeout}s")
```

### Step 4: Run your CLI

```python
if __name__ == "__main__":
    cli()
```

## Automatic Features

When you use `@app_group`, you automatically get:

- **Help options**: `-h` and `--help`
- **Version option**: `--version`
- **Verbosity options**: `-v`, `-vv`, `-vvv` (propagated globally to all subcommands)
- **Configuration option**: `--config` / `-C`
- **Output format option**: `--output-format` / `-o`
- **Environment variable support**: With your custom prefix

## Testing Your CLI

```bash
# Show help
python my_cli.py --help

# Use environment variables
export MYAPP_MESSAGE="Hello from environment!"
python my_cli.py hello

# Use a configuration file
python my_cli.py --config /path/to/config.toml hello

# Use verbosity
python my_cli.py -vv hello --message "Debug mode"
```

## Next Steps

- Learn about [Configuration Management](configuration.md)
- Explore [Output Formatting](output-formatting.md)
- Check out [Complete Examples](examples.md)
- Read the [Development Guide](development.md)
