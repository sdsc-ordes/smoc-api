"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

import typer


cli = typer.Typer(add_completion=False)


# Create command
@cli.command()
def create():
    """Create a digital object."""
    typer.echo("Create a digital object.")
    # Inputs:
    # Name of the object (e.g. assay-xyz)
    #


# inspect command
@cli.command()
def show():
    """Show the contents of a digital object."""
    typer.echo("Inspect a digital object.")
