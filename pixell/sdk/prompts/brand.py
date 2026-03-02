"""Brand context prompt builder for agent system prompts.

Builds a ~50-100 token section that gives agents brand awareness.
Moved from reddit-agent/app/prompts/system.py to centralize across all agents.
"""

from typing import Any


def build_brand_context_section(brand_context: dict[str, Any]) -> str:
    """Build system prompt section with brand context.

    Args:
        brand_context: Dict with brand_name, industry, website, competitors,
                      competitor_details, enrichment_data (all optional).

    Returns:
        Formatted system prompt section string. Empty string if no brand_name.
    """
    brand_name = brand_context.get("brand_name") or brand_context.get("name")
    if not brand_name:
        return ""

    industry = brand_context.get("industry", "")
    website = brand_context.get("website", "")
    competitors = brand_context.get("competitors", [])
    enrichment = brand_context.get("enrichment_data") or {}

    section = f"""## USER'S BRAND CONTEXT

- **Brand Name**: {brand_name}
"""
    if industry:
        section += f"- **Industry**: {industry}\n"
    if website:
        section += f"- **Website**: {website}\n"
    if competitors:
        section += f"- **Tracked Competitors**: {', '.join(str(c) for c in competitors[:10])}\n"

    # Include enrichment summary if available
    if enrichment.get("summary"):
        section += f"\n**About {brand_name}**: {enrichment['summary']}\n"

    section += f"""
When the user says "my brand" or "our product", they mean **{brand_name}**.
When they say "the competitor", they mean the tracked competitors above.

---

"""
    return section
