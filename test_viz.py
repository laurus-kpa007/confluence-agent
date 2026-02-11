import asyncio

async def test():
    from src.router import SourceRouter
    from src.extractor import StructuredExtractor
    import tempfile

    router = SourceRouter()
    
    print("1. Extracting sources...", flush=True)
    sources = [
        "https://developers.googleblog.com/ko/introducing-langextract-a-gemini-powered-information-extraction-library/"
    ]
    contents = []
    for s in sources:
        c = await router.extract(s)
        print(f"   OK: {c.title} ({len(c.text)} chars)", flush=True)
        contents.append(c)
    
    combined = "\n\n".join(c.text[:5000] for c in contents)
    
    print("2. Running LangExtract (gemma2:2b)...", flush=True)
    extractor = StructuredExtractor(model_id="gemma2:2b", model_url="http://localhost:11434")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result, html_str = await extractor.extract_with_visualization(
            combined, profile="tech_review", output_dir=tmpdir,
        )
    
    print(f"3. Extracted {len(result.entities)} entities", flush=True)
    for e in result.entities[:10]:
        cls = e["class"]
        txt = e["text"][:60]
        print(f"   [{cls}] {txt}", flush=True)
    
    with open("viz_output.html", "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"4. Saved viz_output.html ({len(html_str)} chars)", flush=True)

asyncio.run(test())
