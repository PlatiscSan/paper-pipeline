"""Page-preserving character chunking."""


def chunk_pages(pages: list[str], limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for page in pages:
        if current and size + len(page) + 2 > limit:
            chunks.append("\n\n".join(current))
            current = []
            size = 0
        if len(page) > limit:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                size = 0
            marker, _, body = page.partition("\n")
            chunks.extend(
                f"{marker}\n{body[i : i + limit - len(marker) - 1]}"
                for i in range(0, len(body), limit - len(marker) - 1)
            )
        else:
            current.append(page)
            size += len(page) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks
