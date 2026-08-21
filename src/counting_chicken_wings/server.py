"""MCP registration for counting-chicken-wings.

Honesty contract (also in every tool description): every figure cites a source
in sources.yaml. Never conflate required (supply-chain birds) with distinct
(individuals on the plate). There is no bare-number tool.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, tools

server = MCPServer(
    name="counting-chicken-wings",
    title="counting-chicken-wings (cited poultry counts)",
    version=__version__,
    instructions=(
        "How many chickens (or other individuals) does a plate of product "
        "represent — from a cited corpus. Every published number traces to a "
        "real source.\n\n"
        "Honesty contract:\n"
        "- Never invent figures. Prefer wings_calculate / wings_sources over "
        "memory.\n"
        "- Never conflate answer.required (birds' worth of wing through the "
        "funnel) with answer.distinct (expected individuals on the plate).\n"
        "- Trace steps carry source slugs; resolve them in the top-level "
        "sources map. If a step has no source, do not present the figure.\n"
        "- Start with wings_meta / wings_scope, then wings_calculate.\n\n"
        "Site: https://wings.swamplink.com/ · "
        "Project: github.com/gmhoward9289-ops/counting-chicken-wings"
    ),
)


def _read_only(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


@server.tool(name="wings_meta", annotations=_read_only("Corpus meta"))
async def wings_meta() -> Dict[str, Any]:
    """List products, supply chains, loss stages, and mixing stages.

    Call this before calculate so you know which product/chain slugs exist.
    """
    return tools.wings_meta()


@server.tool(name="wings_scope", annotations=_read_only("Species scope"))
async def wings_scope(
    product: Annotated[
        Optional[str],
        Field(description="Product slug, e.g. whole_wing; omit for corpus-wide"),
    ] = None,
) -> Dict[str, Any]:
    """Species coverage depth, corpus anchor, and borrow notes for a product.

    Use when the user picks a non-anchor product and a view might borrow
    another species' numbers.
    """
    return tools.wings_scope(product=product)


@server.tool(name="wings_calculate", annotations=_read_only("Calculate"))
async def wings_calculate(
    count: Annotated[
        float, Field(description="How many units (default 12 = a dozen)", gt=0)
    ] = 12,
    product: Annotated[
        str, Field(description="Product slug from wings_meta")
    ] = "whole_wing",
    chain: Annotated[
        Optional[str],
        Field(description="Supply-chain slug; default is the species default"),
    ] = None,
    pieces: Annotated[
        bool, Field(description="Treat count as segment pieces, not whole units")
    ] = False,
    include_mortality: Annotated[
        bool, Field(description="Include optional mortality loss stages")
    ] = False,
    iterations: Annotated[
        int, Field(description="Monte Carlo iterations (0 = deterministic mode)")
    ] = 0,
    window_days: Annotated[
        Optional[float],
        Field(description="Window for recurring products (eggs, syrup); omit for wings"),
    ] = None,
) -> Dict[str, Any]:
    """Cited answer for a plate of product.

    Returns question, answer (floor/required/distinct/ceiling), per-stage
    trace with source slugs, and a sources map. Say required and distinct
    aloud as different numbers — they answer different questions.
    """
    return tools.wings_calculate(
        count=count,
        product=product,
        chain=chain,
        pieces=pieces,
        include_mortality=include_mortality,
        iterations=iterations,
        window_days=window_days,
    )


@server.tool(name="wings_sources", annotations=_read_only("Citation catalog"))
async def wings_sources() -> Dict[str, Any]:
    """Every source in the corpus, with how many figures cite it."""
    return tools.wings_sources()


@server.tool(name="wings_facts", annotations=_read_only("Fact deck"))
async def wings_facts(
    placement: Annotated[
        str, Field(description="Fact placement bucket, e.g. learning")
    ] = "learning",
    limit: Annotated[int, Field(description="Max facts to return", ge=1, le=1000)] = 20,
) -> Dict[str, Any]:
    """Surprising cited facts with embedded source fields."""
    return tools.wings_facts(placement=placement, limit=limit)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
