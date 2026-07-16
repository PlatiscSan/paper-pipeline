from pathlib import Path

import aiohttp
from aiohttp import web
from paper_pipeline.download.client import DownloadClient
from paper_pipeline.download.models import Candidate


async def test_pdf_and_range(unused_tcp_port: int, tmp_path: Path) -> None:
    payload = b"%PDF-1.7\ncontent"

    async def handler(request: web.Request) -> web.Response:
        start = int(request.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
        return web.Response(
            body=payload[start:],
            status=206 if start else 200,
            headers={"Content-Type": "application/pdf"},
        )

    app = web.Application()
    app.router.add_get("/paper.pdf", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    target = tmp_path / "paper.pdf"
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:{unused_tcp_port}/paper.pdf"
        result = await DownloadClient(session, delay=0).fetch(Candidate(url, "test"), target)
    await runner.cleanup()
    assert result.status == "downloaded" and target.read_bytes() == payload
