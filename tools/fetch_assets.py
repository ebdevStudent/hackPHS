"""Download the CC0 Poly Haven assets the simulator uses into static/assets/.
Run once (or again to fill in anything missing):  python tools/fetch_assets.py
All assets: CC0 by Poly Haven (polyhaven.com) — no attribution required, credited in ASSETS.md anyway."""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "assets")
UA = {"User-Agent": "BallDroneSim/1.0 (hackathon project)"}

HDRIS = {"empty_warehouse_01": "1k", "unfinished_office_night": "1k", "rogland_moonlit_night": "2k"}
TEXTURES = {
    # industrial
    "concrete_floor_worn_001": "2k", "corrugated_iron_02": "1k", "concrete_wall_008": "1k", "blue_metal_plate": "1k",
    "green_metal_rust": "1k", "metal_plate": "1k", "rusty_metal_02": "1k", "painted_concrete": "1k", "metal_grate_rusty": "1k",
    # rescue
    "damaged_plaster": "1k", "factory_brick": "1k", "concrete_floor_damaged_01": "2k", "concrete_debris": "1k",
    "asphalt_02": "1k", "dirty_concrete": "1k", "old_planks_02": "1k", "peeling_painted_wall": "1k",
}
MODELS = [
    # industrial
    "Barrel_01", "Barrel_02", "barrel_03", "wooden_crate_01", "wooden_crate_02", "cardboard_box_01", "plastic_crate_01",
    "metal_jerrycan", "propane_tank", "industrial_storage_cart", "portable_generator", "tool_cart", "metal_tool_chest",
    "worn_metal_rack", "hanging_industrial_lamp", "power_box_01", "korean_fire_extinguisher_01", "ladder_sectioned_01",
    "portable_welding_cart", "concrete_road_barrier", "utility_box_01", "industrial_pastic_container",
    # rescue
    "wooden_bookshelf_worn", "metal_office_desk", "SchoolChair_01", "Sofa_01", "drawer_cabinet", "metal_trash_can",
    "painted_wooden_cabinet", "WoodenTable_01", "street_lamp_01", "caged_hanging_light", "security_light", "portable_searchlight",
]


def api(asset):
    return json.load(urllib.request.urlopen(urllib.request.Request("https://api.polyhaven.com/files/" + asset, headers=UA)))


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()
    open(path, "wb").write(data)
    return len(data)


def jobs():
    for name, res in HDRIS.items():
        f = api(name)["hdri"][res]["hdr"]
        yield f["url"], os.path.join(ROOT, "hdri", f"{name}_{res}.hdr")
    for name, res in TEXTURES.items():
        f = api(name)
        for key, short in (("Diffuse", "diff"), ("nor_gl", "nor"), ("arm", "arm")):
            yield f[key][res]["jpg"]["url"], os.path.join(ROOT, "textures", name, f"{short}.jpg")
    for name in MODELS:
        g = api(name)["gltf"]["1k"]["gltf"]
        yield g["url"], os.path.join(ROOT, "models", name, os.path.basename(g["url"]))
        for rel, inc in g["include"].items():
            yield inc["url"], os.path.join(ROOT, "models", name, *rel.split("/"))


if __name__ == "__main__":
    todo = list(jobs())
    with ThreadPoolExecutor(8) as ex:
        sizes = list(ex.map(lambda j: download(*j), todo))
    print(f"{len(todo)} files, {sum(sizes) / 1e6:.1f} MB downloaded now")
    sys.exit(0)
