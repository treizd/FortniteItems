import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("api_key") # CREATE .ENV FILE AND PASTE API KEY THERE

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bp_path = os.path.join(base_dir, "files", "json", "battlepasses.json") # ADJUST AS NEEDED
items_path = os.path.join(base_dir, "files", "json", "every_item.json") # ADJUST AS NEEDED

async def remove_duplicates(seq):
    seen = set()
    new_seq = []
    for item in seq:
        if item["id"] not in seen:
            seen.add(item["id"])
            new_seq.append(item)
    return new_seq


async def load_bp(language_code="en"):
    current_season = 37 # SET CURRENT SEASON MANUALLY !
    categories = [
        "outfits", "pickaxes", "emotes", "backpacks", "toys", "emojis",
        "gliders", "loading_screens", "sprays", "wraps", "contrails"
    ]

    seasons = {}
    items_path = os.path.join(base_dir, "files", "json", "every_item.json")

    with open(items_path, "r", encoding="utf-8") as f:
        outfits = json.load(f)["outfits"]

    oids = [i["id"] for i in outfits]

    async with aiohttp.ClientSession() as session:
        for n in range(2, current_season + 1):
            url = f"https://fortniteapi.io/v2/battlepass?lang={language_code}&season={n}"

            headers = {"Authorization": api_key}

            async with session.get(url, headers=headers) as response:
                data = await response.json()

            info = {o: [] for o in categories}

            for item in data.get("rewards", []):
                item_type = item.get("item", {}).get("type", {}).get("id", "").lower()
                item_id = item.get("item", {}).get("id", "")
                if item_type == "outfit" and (item_id.startswith("CID") or item_id.startswith("Character")):
                    idX = next((oid for oid in oids if item_id.replace("VTID_", "").replace("_StyleA", "") in oid), None)
                    info["outfits"].append({
                        "id": idX or item_id.replace("VTID_", "").replace("_StyleA", ""),
                        "name": item.get("item", {}).get("name", ""),
                        "rarity": item.get("item", {}).get("rarity", {}).get("id", ""),
                        "tier": item.get("levelsNeededForUnlock", item.get("tier", "")),
                        "season_name": item.get("item", {}).get("battlepass", {}).get("displayText", {}).get("chapterSeason", "")
                    })
                elif item_type in categories:
                    info[item_type].append({
                        "id": item_id,
                        "name": item.get("item", {}).get("name", ""),
                        "rarity": item.get("item", {}).get("rarity", {}).get("id", ""),
                        "tier": item.get("levelsNeededForUnlock", item.get("tier", "")),
                        "season_name": item.get("item", {}).get("battlepass", {}).get("displayText", {}).get("chapterSeason", "")
                    })

            seasons[n] = info

    with open(bp_path, "w", encoding="utf-8") as f:
        json.dump(seasons, f, indent=4, ensure_ascii=False)

async def fetch_data(session, url, language_code):
    async with session.get(url) as response:
        data = await response.json()
        for item in data["data"]["br"]:
            item["name"] = item["name"][language_code] if language_code in item["name"] else item["name"]["en"]
        return data

async def sort_items(items):
    rarity_order = {
        "Mythic": 0, "Legendary": 1, "DARK SERIES": 2, "Slurp Series": 3,
        "Star Wars Series": 4, "MARVEL SERIES": 5, "Lava Series": 6,
        "Frozen Series": 7, "Gaming Legends Series": 8, "Shadow Series": 9,
        "Icon Series": 10, "DC SERIES": 11, "Epic": 12, "Rare": 13,
        "Uncommon": 14, "Common": 15
    }

    def sorting_key(item):
        rarity_value = rarity_order.get(item["rarity"], 100)
        return (rarity_value, item["id"])

    return sorted(items, key=sorting_key)


async def parse(language_code="en"):
    item_data_dict = {category: [] for category in [
        "outfits", "pickaxes", "emotes", "backpacks", "toys", "emojis",
        "gliders", "loading_screens", "sprays", "wraps", "contrails"
    ]}

    async with aiohttp.ClientSession() as session:
        response = await fetch_data(session, "https://fortnite-api.com/v2/cosmetics?language=" + language_code, language_code)
        items = response["data"]["br"]

    for item in items:
        item_type = item["type"]["value"]
        item_data_dict[item_type].append({
            "id": item["id"],
            "name": item["name"] if language_code == "en" else item["name"][language_code],
            "rarity": item["rarity"]["displayValue"],
            "files": {
                "big_icon": item["images"].get("icon"),
                "small_icon": item["images"].get("smallIcon"),
                "featured": item["images"].get("featured")
            }
        })

    for category in item_data_dict:
        item_data_dict[category] = await sort_items(item_data_dict[category])

    with open(items_path, "w", encoding="utf-8") as f:
        json.dump(item_data_dict, f, indent=4, ensure_ascii=False)

    print("Items parsing and saving completed")

async def main():
    language_code = "en" # SUPPORTED LANGUAGE CODES ARE MENTIONED IN README.MD
    await parse(language_code)
    await load_bp(language_code)

    print("All processes were finished")


if __name__ == "__main__":
    asyncio.run(main())
