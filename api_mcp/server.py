from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import app


def _slugify(text: str) -> str:
    """Simple slugifier to create valid MCP tool names."""
    import re

    if not text:
        return ""
    slug = re.sub(r"[\s\-\.]+", "_", text)
    slug = re.sub(r"[^a-zA-Z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug.lower()


def _component_customizer(route, component):
    """Customize generated MCP component names and tags.

    This function runs for every generated component coming from the FastAPI
    OpenAPI spec. We set predictable, slugified tool names (for tools) so that
    LLMs and clients can call them by intuitive names.
    """
    try:
        # Prefer operationId/summary when available, otherwise use method+path
        base = route.operation_id or route.summary or f"{route.method}_{route.path}"
        name = _slugify(base)
        # Namespace to avoid collisions with other servers
        component.name = f"ecommerce_{name}"

        # Ensure every component has an 'ecommerce' tag for filtering
        if hasattr(component, "tags"):
            component.tags = set(getattr(component, "tags", set())) | {"ecommerce"}
    except Exception:
        # Best-effort customization; don't raise here
        pass


# Create an MCP server from the FastAPI app. The `mcp_component_fn` callback
# allows us to mutate tool/resource names and descriptions before they're
# registered. By default FastMCP turns routes into tools, so this makes the
# endpoints directly callable by LLMs as MCP tools.
mcp = FastMCP.from_fastapi(
    app,
    name="E-Commerce MCP Server",
    mcp_component_fn=_component_customizer,
    tags={"ecommerce"},
)


# @mcp.custom_route("/health", methods=["GET"])
# async def health_check(request: Request):
#     return JSONResponse({"status": "healthy"})


if __name__ == "__main__":
    # Print available tool names so developers can see what was registered.
    try:
        tools = list(mcp.tool_manager._tools.keys())
        print("Registered MCP tools:")
        for t in sorted(tools):
            print(" -", t)
    except Exception:
        pass

    mcp.run(transport="streamable-http", host="localhost", port=8020)
