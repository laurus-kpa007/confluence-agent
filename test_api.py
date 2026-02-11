"""Test entity extraction API"""
import asyncio
import aiohttp

async def test_extract_entities():
    url = "http://127.0.0.1:8501/api/extract_entities"
    data = {
        "sources": ["test_meeting.txt"],
        "profile": "meeting"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as resp:
                print(f"Status: {resp.status}")
                result = await resp.json()

                if result.get("ok"):
                    print(f"✅ Success!")
                    print(f"Profile: {result['profile']}")
                    print(f"Total entities: {result['total_count']}")
                    print(f"\nEntities:")
                    for i, entity in enumerate(result['entities'][:3], 1):
                        print(f"\n{i}. [{entity['type']}] - {entity['confidence']*100:.0f}%")
                        print(f"   Content: {entity['content'][:100]}...")
                        if entity['fields']:
                            for k, v in entity['fields'].items():
                                print(f"   {k}: {v}")
                else:
                    print(f"❌ Error: {result.get('error')}")
                    print(result.get('traceback', ''))
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_extract_entities())
