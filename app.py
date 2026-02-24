from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from db import get_connection

app = FastAPI(title="Food Web Backend")

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Static Images
# ----------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================
# ECOSYSTEM VIEW (Merged Webs)
# ============================================================
@app.get("/ecosystems/{ecosystem_id}")
def get_ecosystem(ecosystem_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Get all webs in ecosystem
    cursor.execute("""
        SELECT id
        FROM food_webs
        WHERE ecosystem_id = %s
    """, (ecosystem_id,))
    webs = cursor.fetchall()

    if not webs:
        conn.close()
        return {"nodes": [], "edges": []}

    web_ids = [w["id"] for w in webs]
    format_strings = ",".join(["%s"] * len(web_ids))

    # 2️⃣ Get ALL organisms in those webs (IMPORTANT FIX)
    cursor.execute(f"""
        SELECT wo.web_id,
               o.id,
               o.common_name,
               o.scientific_name,
               o.trophic_level,
               o.image_url
        FROM web_organisms wo
        JOIN organisms o ON wo.organism_id = o.id
        WHERE wo.web_id IN ({format_strings})
    """, tuple(web_ids))

    raw_nodes = cursor.fetchall()

    # Build nodes unique per web
    nodes = []
    for n in raw_nodes:
        nodes.append({
            "id": f"{n['web_id']}-{n['id']}",  # unique per web
            "organism_id": n["id"],
            "common_name": n["common_name"],
            "scientific_name": n["scientific_name"],
            "trophic_level": n["trophic_level"],
            "image_url": n["image_url"],
            "web_id": n["web_id"]
        })

    # 3️⃣ Get all edges for those webs
    cursor.execute(f"""
        SELECT web_id,
               predator_id,
               prey_id,
               feed_type
        FROM feeding_relationships
        WHERE web_id IN ({format_strings})
    """, tuple(web_ids))

    raw_edges = cursor.fetchall()

    edges = []
    for e in raw_edges:
        edges.append({
            "web_id": e["web_id"],
            "from": f"{e['web_id']}-{e['predator_id']}",
            "to": f"{e['web_id']}-{e['prey_id']}",
            "feed_type": e["feed_type"]
        })

    conn.close()

    return {
        "nodes": nodes,
        "edges": edges
    }



# ============================================================
# LIST ECOSYSTEMS
# ============================================================
@app.get("/ecosystems")
def list_ecosystems():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name
        FROM ecosystems
    """)

    ecosystems = cursor.fetchall()
    conn.close()

    return ecosystems


# ============================================================
# LIST WEBS IN ECOSYSTEM
# ============================================================
@app.get("/ecosystems/{ecosystem_id}/webs")
def get_webs(ecosystem_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name
        FROM food_webs
        WHERE ecosystem_id = %s
    """, (ecosystem_id,))

    webs = cursor.fetchall()
    conn.close()

    return {"webs": webs}


# ============================================================
# SINGLE WEB VIEW (Zoom)
# ============================================================
@app.get("/food-webs/{web_id}")
def get_single_food_web(web_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Get relationships for this web
    cursor.execute("""
        SELECT predator_id AS `from`,
               prey_id AS `to`,
               feed_type
        FROM feeding_relationships
        WHERE web_id = %s
    """, (web_id,))

    edges = cursor.fetchall()

    if not edges:
        conn.close()
        return {"nodes": [], "edges": []}

    # 2️⃣ Collect organism IDs
    organism_ids = set()
    for e in edges:
        organism_ids.add(e["from"])
        organism_ids.add(e["to"])

    format_strings = ",".join(["%s"] * len(organism_ids))

    # 3️⃣ Get organism data
    cursor.execute(f"""
        SELECT id,
               common_name,
               scientific_name,
               trophic_level,
               image_url
        FROM organisms
        WHERE id IN ({format_strings})
    """, tuple(organism_ids))

    nodes = cursor.fetchall()

    conn.close()

    return {
        "nodes": nodes,
        "edges": edges
    }


# ============================================================
# CREATE ORGANISM
# ============================================================
@app.post("/organisms")
def create_organism(
    common_name: str = Form(...),
    scientific_name: str = Form(...),
    trophic_level: str = Form(...),
    image: UploadFile | None = File(None)
):
    image_url = None

    if image:
        upload_dir = "static/images"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, image.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        image_url = f"/static/images/{image.filename}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO organisms (common_name, scientific_name, trophic_level, image_url)
        VALUES (%s, %s, %s, %s)
    """, (common_name, scientific_name, trophic_level, image_url))

    conn.commit()
    conn.close()

    return {"message": "Organism created successfully"}


# ============================================================
# LIST ALL FOOD WEBS
# ============================================================
@app.get("/food-webs")
def list_food_webs():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, ecosystem_id
        FROM food_webs
    """)

    webs = cursor.fetchall()
    conn.close()

    return webs
