import logging
from dagster import (
    asset, 
    AssetExecutionContext, 
    Config, 
    Definitions, 
    ScheduleDefinition, 
    define_asset_job,
    RetryPolicy
)
from web.scraper import WebScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScrapingConfig(Config):
    """Configuration for web scraping assets."""
    base_url: str
    max_depth: int = 1
    include_images: bool = True
    include_links: bool = True
    user_agent: str = "Mozilla/5.0 (compatible; InsightMesh/1.0; +https://insightmesh.com)"
    rate_limit_delay: float = 1.0

@asset(
    retry_policy=RetryPolicy(max_retries=3, delay=60),  # Web scraping may need longer delays between retries
)
def scrape_website(context: AssetExecutionContext, config: WebScrapingConfig):
    """Asset to scrape a website and store its content in Neo4j and Elasticsearch."""
    try:
        scraper = WebScraper(
            base_url=config.base_url,
            max_depth=config.max_depth,
            include_images=config.include_images,
            include_links=config.include_links,
            user_agent=config.user_agent,
            rate_limit_delay=config.rate_limit_delay
        )
        result = scraper.scrape_site()
        context.add_output_metadata({
            "pages_scraped": len(result["scraped_pages"]),
            "total_links": len(result["all_links"]),
            "total_images": len(result["all_images"]),
            "status": "success"
        })
        return result
    except Exception as e:
        logger.error(f"Error during web scraping: {str(e)}")
        context.add_output_metadata({
            "status": "error",
            "error_message": str(e)
        })
        raise

# Define the job
web_scraping_job = define_asset_job(
    name="web_scraping_job",
    selection=[scrape_website]
)

# Define a schedule to run every day at midnight
web_scraping_schedule = ScheduleDefinition(
    job=web_scraping_job,
    cron_schedule="0 0 * * *"  # Run daily at midnight
)

# Create definitions object
defs = Definitions(
    assets=[scrape_website],
    schedules=[web_scraping_schedule],
    jobs=[web_scraping_job]
) 