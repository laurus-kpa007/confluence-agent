import asyncio

async def test():
    from src.router import SourceRouter
    from src.extractor import StructuredExtractor
    from src.compare_viz import generate_comparison_html
    import tempfile

    router = SourceRouter()
    
    print("1. Extracting source...", flush=True)
    c = await router.extract(
        "https://developers.googleblog.com/ko/introducing-langextract-a-gemini-powered-information-extraction-library/"
    )
    print(f"   OK: {len(c.text)} chars", flush=True)
    
    print("2. Running LangExtract...", flush=True)
    extractor = StructuredExtractor(model_id="gemma2:2b", model_url="http://localhost:11434")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result, _ = await extractor.extract_with_visualization(
            c.text[:5000], profile="tech_review", output_dir=tmpdir,
        )
    
    print(f"3. Generating comparison view ({len(result.entities)} entities)...", flush=True)
    comparison_html = generate_comparison_html(
        original_text=c.text[:5000],
        entities=result.entities,
        title="LangExtract 기술 분석",
    )
    
    with open("compare_output.html", "w", encoding="utf-8") as f:
        f.write(comparison_html)
    print("4. Saved compare_output.html", flush=True)
    
    # Screenshot with Playwright
    print("5. Capturing screenshot...", flush=True)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.set_content(comparison_html)
        await page.wait_for_timeout(1500)
        await page.screenshot(path="compare_screenshot.png", full_page=False)
        print("   Saved compare_screenshot.png", flush=True)
        await browser.close()

asyncio.run(test())
