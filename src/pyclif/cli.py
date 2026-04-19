"""Console script for pyclif."""

from pyclif import app_group

from .apps import groups


@app_group(handle_response=True)
def app():
    """pyclif — CLI framework and project scaffolding."""


for group in groups:
    app.add_command(group)


if __name__ == "__main__":
    app()
