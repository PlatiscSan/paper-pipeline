import xml.etree.ElementTree as ET

from paper_pipeline.search.base import allocate, parse_years
from paper_pipeline.search.pubmed import parse_article, recursive_text


def test_year_and_allocation() -> None:
    assert parse_years("2022-2026") == (2022, 2026)
    assert parse_years("2024") == (2024, 2024)
    assert allocate(5, ["arxiv", "pubmed"]) == {"arxiv": 3, "pubmed": 2}


def test_pubmed_recursive_text() -> None:
    node = ET.fromstring("<ArticleTitle>CO<sub>2</sub> and x<sup>2</sup></ArticleTitle>")
    assert recursive_text(node) == "CO2 and x2"
    article = ET.fromstring(
        """<PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
        <ArticleTitle>Dry <i>reforming</i></ArticleTitle><Abstract>
        <AbstractText>A<sub>2</sub></AbstractText></Abstract><Journal><JournalIssue>
        <PubDate><Year>2024</Year></PubDate></JournalIssue></Journal></Article>
        </MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">
        10.1/x</ArticleId></ArticleIdList></PubmedData></PubmedArticle>"""
    )
    result = parse_article(article)
    assert result.title == "Dry reforming" and result.abstract == "A2" and result.year == 2024
