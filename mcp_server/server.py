import logging, time
from mcp.server.mcpserver.exceptions import ToolError
from langsmith import traceable

@traceable(name="procurement_tool",run_type="tool")
def execute(fn,data):
    start=time.perf_counter()
    try:
        result=fn(data)
        logging.info("tool=%s status=ok elapsed=%.3f",fn.__name__,time.perf_counter()-start)
        return result
    except ValueError as exc:
        logging.info("tool=%s status=rejected reason=%s",fn.__name__,str(exc))
        raise ToolError(str(exc)) from None
from mcp.server.mcpserver import MCPServer
from backend.database import init_db
from backend.schemas import SearchInput, CompareInput, BudgetInput, DetailInput, OrderInput, EmailInput
from backend.services import catalog, orders, email
from backend.schemas import OfferOutput, ComparisonOutput, BudgetOutput, OrderOutput, EmailOutput
mcp=MCPServer('techstock-mcp')

@mcp.tool()
def search_products(data: SearchInput) -> list[OfferOutput]:
    """Search eligible local catalog offers using hard technical and budget constraints."""
    return [OfferOutput.model_validate(x) for x in execute(catalog.search_products,data)]
@mcp.tool()
def compare_offers(data: CompareInput) -> list[ComparisonOutput]:
    """Recheck requirements and rank offers by total price and freshness."""
    return [ComparisonOutput.model_validate(x) for x in execute(catalog.compare_offers,data)]
@mcp.tool()
def check_budget(data: BudgetInput) -> BudgetOutput:
    """Calculate total and remaining TND budget using stored prices."""
    return BudgetOutput.model_validate(execute(catalog.check_budget,data))
@mcp.tool()
def get_offer_details(data: DetailInput) -> OfferOutput:
    """Return one stored offer, source URL, specifications and timestamp."""
    return OfferOutput.model_validate(execute(catalog.get_offer_details,data))
@mcp.tool()
def create_purchase_order(data: OrderInput) -> OrderOutput:
    """Create an idempotent sandbox order only from a trusted approved proposal."""
    return OrderOutput.model_validate(execute(orders.create_purchase_order,data))
@mcp.tool()
def send_confirmation_email(data: EmailInput) -> EmailOutput:
    """Deliver durable outbox notification to the approved order recipient."""
    return EmailOutput.model_validate(execute(email.send_confirmation_email,data))

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    init_db(); mcp.run(transport='stdio')
