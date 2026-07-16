"""Resolve only explicitly open-access PDF candidates."""

import re

import aiohttp
from paper_pipeline.db.models import Paper
from paper_pipeline.download.models import Candidate


class Resolver:
    def __init__(
        self, session: aiohttp.ClientSession, email: str = "", semantic_key: str = ""
    ) -> None:
        self.session, self.email, self.semantic_key = session, email, semantic_key

    async def candidates(self, paper: Paper) -> list[Candidate]:
        result: list[Candidate] = []
        if paper.pdf_url:
            result.append(Candidate(paper.pdf_url, "metadata"))
        if paper.arxiv_id:
            result.append(Candidate(f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf", "arxiv"))
        if paper.pmcid:
            result.append(
                Candidate(
                    f"https://www.ebi.ac.uk/europepmc/webservices/rest/{paper.pmcid}/fullTextPDF",
                    "europe_pmc",
                )
            )
            result.extend(await self._pmc(paper.pmcid))
        if paper.doi and self.email:
            result.extend(await self._unpaywall(paper.doi))
        if paper.doi and self.semantic_key:
            result.extend(await self._semantic(paper.doi))
        if paper.url:
            result.extend(await self._landing(paper.url))
        unique: dict[str, Candidate] = {}
        for item in result:
            unique.setdefault(item.url, item)
        return list(unique.values())

    async def _pmc(self, pmcid: str) -> list[Candidate]:
        url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
        try:
            async with self.session.get(url) as response:
                text = await response.text()
            hrefs = re.findall(r'href="([^"]+)"', text)
            return [Candidate(x, "pmc") for x in hrefs if x.lower().endswith(".pdf")]
        except aiohttp.ClientError:
            return []

    async def _unpaywall(self, doi: str) -> list[Candidate]:
        async with self.session.get(
            f"https://api.unpaywall.org/v2/{doi}", params={"email": self.email}
        ) as r:
            if r.status != 200:
                return []
            data = await r.json()
            location = data.get("best_oa_location") or {}
            return (
                [Candidate(location["url_for_pdf"], "unpaywall")]
                if location.get("url_for_pdf")
                else []
            )

    async def _semantic(self, doi: str) -> list[Candidate]:
        headers = {"x-api-key": self.semantic_key}
        async with self.session.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "openAccessPdf"},
            headers=headers,
        ) as r:
            if r.status != 200:
                return []
            value = (await r.json()).get("openAccessPdf") or {}
            return [Candidate(value["url"], "semantic_scholar")] if value.get("url") else []

    async def _landing(self, url: str) -> list[Candidate]:
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                body = await response.text(errors="ignore")
            match = re.search(
                r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)', body, re.I
            )
            return [Candidate(match.group(1), "citation_pdf_url")] if match else []
        except aiohttp.ClientError:
            return []
