"""Table definitions for project scaffolding output."""

from pyclif import CliTable, CliTableColumn, Response


class ScaffoldingTable(CliTable):
    """Table displaying files created or modified by a scaffolding command."""

    _ACTION_LABEL = {
        "created": ":sparkles:  created",
        "modified": ":pencil2:  modified",
    }

    fields = {
        "file": CliTableColumn(header="File"),
        "action": CliTableColumn(header="Action", style="bold green"),
    }

    def __init__(self, response: Response):
        """Initialize the scaffolding table from a command response.

        Args:
            response: The scaffolding command response carrying the files list.
        """
        rows = [
            {"file": r["file"], "action": self._ACTION_LABEL.get(r["action"], r["action"])}
            for r in response.data.get("files", [])
        ]
        total = len(rows)
        super().__init__(
            fields=self.fields,
            rows=rows,
            table_style={
                "title": response.message,
                "caption": f"{total} file{'s' if total != 1 else ''} touched",
            },
        )
