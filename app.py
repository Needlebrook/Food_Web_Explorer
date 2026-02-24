from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from config import ADMIN_PASSWORD
import shutil
import os
from db import get_connection
from typing import Optional, List, Dict
import json

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
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
# ----------------------------
# Static Images
# ----------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----------------------------
# NEW ENDPOINT: Get single organism details
# ----------------------------
@app.get("/organisms/{organism_id}")
def get_organism(organism_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get organism details
    cursor.execute("""
        SELECT id, common_name, scientific_name, trophic_level, image_url
        FROM organisms
        WHERE id = %s
    """, (organism_id,))
    
    organism = cursor.fetchone()
    
    if not organism:
        conn.close()
        raise HTTPException(status_code=404, detail="Organism not found")
    
    # Get what this organism preys on
    cursor.execute("""
        SELECT DISTINCT o2.common_name
        FROM feeding_relationships fr
        JOIN organisms o2 ON fr.prey_id = o2.id
        WHERE fr.predator_id = %s
    """, (organism_id,))
    
    prey = [row["common_name"] for row in cursor.fetchall()]
    
    # Get what preys on this organism
    cursor.execute("""
        SELECT DISTINCT o2.common_name
        FROM feeding_relationships fr
        JOIN organisms o2 ON fr.predator_id = o2.id
        WHERE fr.prey_id = %s
    """, (organism_id,))
    
    predators = [row["common_name"] for row in cursor.fetchall()]
    
    conn.close()
    
    organism["prey"] = prey
    organism["predators"] = predators
    
    return organism

# ----------------------------
# Admin 
# ----------------------------
@app.post("/admin/login")
def admin_login(password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")
    
@app.post("/admin/ecosystems")
def create_ecosystem(
    name: str = Form(...),
    description: str = Form(None)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO ecosystems (name, description)
            VALUES (%s, %s)
        """, (name, description))
        
        conn.commit()
        ecosystem_id = cursor.lastrowid
        
        return {
            "message": "Ecosystem created successfully",
            "ecosystem_id": ecosystem_id
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    
@app.post("/admin/create-web")
async def create_food_web(
    ecosystem_id: int = Form(...),
    web_name: str = Form(...),
    organisms: str = Form(...),  # JSON string
    relationships: str = Form(...),  # JSON string
    images: List[UploadFile] = File(None)
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Parse JSON data
        organisms_data = json.loads(organisms)
        relationships_data = json.loads(relationships)
        
        # Validate ecosystem exists
        cursor.execute("SELECT id FROM ecosystems WHERE id = %s", (ecosystem_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Invalid ecosystem ID")
        
        # Create food web
        cursor.execute("""
            INSERT INTO food_webs (name, ecosystem_id)
            VALUES (%s, %s)
        """, (web_name, ecosystem_id))
        
        web_id = cursor.lastrowid
        
        # Dictionary to store organism IDs
        organism_ids = {}
        
        # Create organisms
        for idx, org_data in enumerate(organisms_data):
            # Check if organism already exists
            cursor.execute("""
                SELECT id FROM organisms 
                WHERE common_name = %s AND scientific_name = %s
            """, (org_data["common_name"], org_data["scientific_name"]))
            
            existing = cursor.fetchone()
            
            if existing:
                organism_id = existing["id"]
            else:
                # Handle image upload
                image_url = None
                if images and idx < len(images) and images[idx].filename:
                    upload_dir = "static/images"
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, images[idx].filename)
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(images[idx].file, buffer)
                    
                    image_url = f"/static/images/{images[idx].filename}"
                
                # Create new organism
                cursor.execute("""
                    INSERT INTO organisms (common_name, scientific_name, trophic_level, image_url)
                    VALUES (%s, %s, %s, %s)
                """, (
                    org_data["common_name"],
                    org_data["scientific_name"],
                    org_data["trophic_level"],
                    image_url
                ))
                
                organism_id = cursor.lastrowid
            
            organism_ids[str(idx)] = organism_id
            
            # Link organism to web
            cursor.execute("""
                INSERT IGNORE INTO web_organisms (web_id, organism_id)
                VALUES (%s, %s)
            """, (web_id, organism_id))
        
        # Validate and create relationships
        for rel_data in relationships_data:
            predator_idx = rel_data["predator"]
            prey_idx = rel_data["prey"]
            feed_type = rel_data["feed_type"]
            
            # Validate indices exist
            if predator_idx not in organism_ids or prey_idx not in organism_ids:
                raise HTTPException(status_code=400, detail="Invalid relationship indices")
            
            predator_id = organism_ids[predator_idx]
            prey_id = organism_ids[prey_idx]
            
            # Validate trophic levels (basic check)
            cursor.execute("SELECT trophic_level FROM organisms WHERE id = %s", (predator_id,))
            predator_level = cursor.fetchone()["trophic_level"]
            
            cursor.execute("SELECT trophic_level FROM organisms WHERE id = %s", (prey_id,))
            prey_level = cursor.fetchone()["trophic_level"]
            
            # Simple validation: predator should be higher or equal in food chain
            level_order = {
                "Producer": 1,
                "Primary Consumer": 2,
                "Secondary Consumer": 3,
                "Apex Predator": 4
            }
            
            if level_order.get(predator_level, 0) <= level_order.get(prey_level, 0):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid relationship: {predator_level} cannot prey on {prey_level}"
                )
            
            # Check if relationship already exists
            cursor.execute("""
                SELECT id FROM feeding_relationships
                WHERE web_id = %s AND predator_id = %s AND prey_id = %s
            """, (web_id, predator_id, prey_id))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO feeding_relationships (web_id, predator_id, prey_id, feed_type)
                    VALUES (%s, %s, %s, %s)
                """, (web_id, predator_id, prey_id, feed_type))
        
        conn.commit()
        return {"message": "Food web created successfully", "web_id": web_id}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ============================================================
# DELETE FOOD WEB (Admin only)
# ============================================================
@app.delete("/admin/webs/{web_id}")
def delete_food_web(web_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First check if web exists
        cursor.execute("SELECT id FROM food_webs WHERE id = %s", (web_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Food web not found")
        
        # Delete feeding relationships first (foreign key constraint)
        cursor.execute("DELETE FROM feeding_relationships WHERE web_id = %s", (web_id,))
        
        # Delete web_organisms entries
        cursor.execute("DELETE FROM web_organisms WHERE web_id = %s", (web_id,))
        
        # Finally delete the food web
        cursor.execute("DELETE FROM food_webs WHERE id = %s", (web_id,))
        
        conn.commit()
        return {"message": "Food web deleted successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

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
