#!/usr/bin/env python

import click
from rich.console import Console

# Shared console instance
console = Console()

def get_verbose_flag(ctx):
    """Get the verbose flag from click context"""
    return ctx.obj.get('VERBOSE', False)

def print_success(message):
    """Print a success message"""
    console.print(f"[green]{message}[/green]")

def print_error(message):
    """Print an error message"""
    console.print(f"[red]{message}[/red]")

def print_warning(message):
    """Print a warning message"""
    console.print(f"[yellow]{message}[/yellow]")

def print_info(message):
    """Print an info message"""
    console.print(f"[blue]{message}[/blue]") 