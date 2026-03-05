class SchemaRegistry:

    def __init__(self, adapter):
        self.adapter = adapter
        self.schema = {}  # Will be populated after async initialization

    async def initialize(self):
        """Load schema asynchronously from adapter"""
        self.schema = await self.adapter.get_schema()

    def get_schema_text(self):
        """Get schema as formatted text"""
        lines = []
        for table, columns in self.schema.items():
            col_string = ", ".join(
                f"{c['column']} ({c['type']})" for c in columns
            )
            lines.append(f"{table}({col_string})")
        return "\n".join(lines)

    def get_columns(self):
        """Get all columns organized by table"""
        cols = {}
        for table, columns in self.schema.items():
            cols[table] = [c['column'] for c in columns]
        return cols