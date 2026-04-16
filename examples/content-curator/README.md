# Content Curator Agent

A research agent that finds and curates relevant content for marketing newsletters.

## What it does

- Searches the web for current information on a given topic
- Evaluates source credibility and recency
- Synthesizes findings into structured briefs with key findings, sources, and suggested angles
- Aligns research with brand voice when brand context is provided

## Inputs

| Input | Required | Description |
|---|---|---|
| `topic` | Yes | The subject to research |
| `brand_context` | No | Brand voice and guidelines to align with |
| `target_audience` | No | Who the content is for |

## Tools needed

- **web_search** (required) — any web search MCP server (e.g., Perplexity)
- **save_notes** (optional) — note-taking MCP server (e.g., Notion)

## Usage

```python
from fylle import parse_fylle_package

agent = parse_fylle_package("content-curator.fylle")
# Pass to your runtime of choice
```
