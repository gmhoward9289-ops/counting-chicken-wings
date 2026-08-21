---
bump: second
---
### Crawl basics at the apex

The live site had a title and nothing else a crawler looks for: no meta
description, no canonical, and both `/robots.txt` and `/sitemap.xml` 404'd
as JSON from FastAPI. Head tags now carry a 160-character description and
`https://wings.swamplink.com/` as the canonical. Those two files are served
at the site root by their own routes — files next to the HTML only reach
`/static/`, which is not where a crawler asks. The sitemap lists the
homepage only.
