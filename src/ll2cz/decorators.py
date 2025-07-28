# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Decorators for CLI commands to reduce code duplication."""

import functools
import sys
from typing import Callable

from rich.console import Console

from .config import Config

console = Console()


def requires_database(func: Callable) -> Callable:
    """Decorator that ensures database configuration is available.

    This decorator handles the common pattern of loading database configuration
    and displaying error messages when configuration is missing.

    The decorated function must accept a 'db_connection' keyword argument.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        config = Config()
        db_connection = kwargs.get('db_connection')

        # Load from config if not provided via CLI
        db_connection = config.get_database_connection(db_connection)

        if not db_connection:
            console.print("[red]Error: --input (database connection) is required[/red]")
            console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            sys.exit(1)

        # Update kwargs with resolved connection
        kwargs['db_connection'] = db_connection
        return func(*args, **kwargs)

    return wrapper


def requires_cloudzero_auth(func: Callable) -> Callable:
    """Decorator that ensures CloudZero API credentials are available.

    This decorator handles loading CloudZero API key and connection ID
    from configuration or CLI arguments.

    The decorated function must accept 'cz_api_key' and 'cz_connection_id' keyword arguments.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        config = Config()

        # Get API key
        cz_api_key = kwargs.get('cz_api_key')
        cz_api_key = config.get_cz_api_key(cz_api_key)

        if not cz_api_key:
            console.print("[red]Error: --cz-api-key (CloudZero API key) is required[/red]")
            console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            sys.exit(1)

        # Get connection ID
        cz_connection_id = kwargs.get('cz_connection_id')
        cz_connection_id = config.get_cz_connection_id(cz_connection_id)

        if not cz_connection_id:
            console.print("[red]Error: --cz-connection-id (CloudZero connection ID) is required[/red]")
            console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            sys.exit(1)

        # Update kwargs with resolved credentials
        kwargs['cz_api_key'] = cz_api_key
        kwargs['cz_connection_id'] = cz_connection_id
        return func(*args, **kwargs)

    return wrapper


def handle_errors(func: Callable) -> Callable:
    """Decorator for consistent error handling in CLI commands.

    Catches exceptions and displays them in a user-friendly format.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            # In debug mode, show full traceback
            import os
            if os.environ.get('LL2CZ_DEBUG'):
                import traceback
                console.print("[dim]Full traceback:[/dim]")
                console.print(traceback.format_exc())
            sys.exit(1)

    return wrapper


def with_progress(message: str = "Processing...") -> Callable:
    """Decorator that shows a progress spinner during command execution.

    Args:
        message: Message to display with the spinner
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(message, total=None)
                try:
                    result = func(*args, **kwargs)
                    progress.update(task, completed=True)
                    return result
                except Exception:
                    progress.stop()
                    raise

        return wrapper
    return decorator
