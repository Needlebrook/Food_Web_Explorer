# 🌿 Food Web Explorer

A web application for exploring and managing ecological food webs across different ecosystems. Built with FastAPI, MySQL/TiDB, and vis-network visualization. Created as the final project for the DBMS course in B.Tech CSE Semester 4.

Development Period : February - March 2026

Available at: https://food-web-explorer.onrender.com/ or https://food-web-explorer.vercel.app/

## 📋 Project Overview

Food Web Explorer is an interactive database management system that allows users to visualize complex feeding relationships in various ecosystems. The application demonstrates fundamental DBMS concepts including DDL, DML, multi-table relationships, JOIN operations, aggregate functions, views, triggers, and integrity constraints.

### Key Features

- **Interactive Food Web Visualization** - Color-coded nodes representing trophic levels with directional arrows showing energy flow
- **Multi-Ecosystem Support** - Manage food webs across Forest, Grassland, Marine, and Freshwater ecosystems
- **Complete CRUD Operations** - Create, Read, Update, and Delete food webs through an intuitive admin interface
- **Species Details Modal** - Click any node to view scientific names, trophic levels, and predator/prey relationships
- **Statistics Dashboard** - View aggregated data including species counts, trophic distribution, and ecosystem summaries
- **Educational Info Modals** - Encyclopedia-style information about ecosystems and how to read food webs
- **Admin Authentication** - Secure login for data management operations

## 🎮 How to Use

### Regular User
  1. Browse ecosystems :- Click ecosystem buttons to view all food webs
  2. Explore webs :- Click on edges (arrows) to zoom into specific food webs
  3. View species details :- Click on any node to see scientific name, trophic level, and relationships
  4. Learn :- Click "About Ecosystems" or "How to Read Food Webs" for educational content
  5. View statistics :- Click "Statistics" for aggregated data

### Admin User

  1. Login :- Click "Log in as Admin" (password: set in config.py)
  2. Create new web :- Fill out the form with organisms and feeding relationships
  3. Edit existing web :- Use the edit section to rename or move webs between ecosystems
  4. Delete web :- Use the delete section to remove webs (cascade deletes relationships)

## 📈 Statistics Dashboard
### The statistics endpoint (/stats) provides:

  - Total counts : Organisms, food webs, ecosystems
  - Trophic distribution : Counts by trophic level
  - Average prey per predator : Ecological network metric
  - Most connected species : Species with most relationships
  - View data : Data from ecosystem_stats and food_web_details views

## 🔒 Data Validation & Integrity

| Layer | Validation | 
|---|---|
|Frontend	| JavaScript checks for empty fields, duplicate organisms, valid relationships|
|Backend	| Python validates trophic hierarchy, feed type consistency, circular relationships|
|Database	| CHECK constraints, foreign keys, triggers (local MySQL) prevent invalid data|

### Validation Rules

  - Producers cannot be predators
  - Organisms cannot prey on themselves
  - Predators must be at higher trophic levels than prey
  - Herbivores can only eat producers
  - No circular feeding relationships

## 🗄️ Database Schema

The application uses a normalized relational database with five interconnected tables:

```sql
ecosystems (id, name, description)
food_webs (id, name, ecosystem_id) → FK references ecosystems
organisms (id, common_name, scientific_name, trophic_level, image_url)
web_organisms (web_id, organism_id) → Junction table (M:N relationship)
feeding_relationships (id, web_id, predator_id, prey_id, feed_type)
```
## 🌟 Database Design Highlights 

- **Normalization**: 3NF compliant with no redundancy
- **Constraints**: PRIMARY KEY, FOREIGN KEY, NOT NULL, UNIQUE, CHECK
- **Relationships**: One-to-Many (ecosystems → webs), Many-to-Many (webs ↔ organisms)
- **Triggers**: Prevent invalid feeding relationships (local MySQL)

## 📊 DBMS Concepts Demonstrated

1. DDL (Data Definition Language)

    - Complete table creation with proper data types and constraints
    - Primary keys, foreign keys, and composite keys
    - CHECK constraints for trophic levels

2. DML (Data Manipulation Language)

    - INSERT: Create new ecosystems, food webs, organisms, and relationships
    - UPDATE: Modify food web names and move between ecosystems
    - DELETE: Remove food webs with cascade deletion

3. Multi-Table JOIN Operations
   
4. Aggregate Functions

    - COUNT() – Total organisms per trophic level
    - AVG() – Average prey per predator
    - GROUP BY – Trophic level distribution

5. Views
    - ecosystem_stats – Summary of species counts per ecosystem
    - food_web_details – Web-level statistics
  
6. Triggers (Local MySQL, not applicable to TiDB)

    - prevent_producer_predator – Prevents producers from being predators
    - log_web_changes – Automatically logs food web updates

7. Integrity Constraints

    - Foreign key constraints with CASCADE DELETE
    - NOT NULL constraints on required fields
    - UNIQUE constraint on junction table

## 🔌API endpoints

| Endpoint | Method | Description |
|---|---|---|
/ |	GET |	Serve frontend HTML
/ecosystems |	GET	| List all ecosystems
/ecosystems/{id} | GET	| Get merged food web view
/ecosystems/{id}/webs	| GET	| List webs in ecosystem
/food-webs/{id}	| GET	| Get single web details
/food-webs/{id}/details |	GET	| Get web name only
/organisms/{id}	| GET	| Get species details with prey/predators
/stats	| GET	|Statistics with aggregates and views
/admin/login |	POST	| Admin authentication
/admin/ecosystems	| POST	| Create new ecosystem
/admin/create-web	| POST	| Create new food web
/admin/webs/{id}	| PUT	| Update food web
/admin/webs/{id}	| DELETE	| Delete food web
/organisms	| POST	| Create new organism

## 📁 Project Structure
``` bash
food-web-explorer/
├── app.py                 # FastAPI backend with all endpoints
├── db.py                  # Database connection handler
├── config.py              # Configuration (admin password)
├── schemas.py             # Pydantic models for request/response validation
├── requirements.txt       # Python dependencies
├── index.html             # Frontend HTML/CSS/JavaScript
├── render.yaml            # Render deployment configuration
├── static/                # Static files (images, etc.)
│   └── images/            # Uploaded species images
└── README.md              # This file
```
## 🗄️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MySQL & TiDB Cloud
- **Frontend**: HTML5, CSS, Bootstrap 5
- **Visualization**: vis-network.js
- **Deployment**: Render + TiDB Cloud

## 🛠️ Installation & Setup

### Prerequisites

  - Python 3.8+
  - MySQL 8.0 (local development) or TiDB Cloud account
  - Git

### Local Execution
  
1. Clone the repository
``` bash
git clone https://github.com/yourusername/food-web-explorer.git
cd food-web-explorer
```

2. Create and activate virtual environment
``` bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Dependencies
``` bash
pip install -r requirements.txt
```

4. Set up the database
``` sql
-- Create database
CREATE DATABASE food_web;
USE food_web;

-- Import schema (from the SQL dump provided)
SOURCE foodweb_backup.sql;
```
5. Configure database connection
Update db.py with your local MySQL credentials:
``` python
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="food_web"
    )
```
6. Run the application
``` bash
uvicorn app:app --reload
```
7. Access the application
Open your browser at http://localhost:8000

### Cloud Deployment (Render + TiDB)

- Push code to GitHub
- Create TiDB Cloud account (free tier)
- Import your database to TiDB
- Connect Render to GitHub repository
- Add environment variables in Render dashboard:  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
- Deploy: Render will automatically build and deploy

## 📚 Documentation References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MySQL Connector/Python](https://dev.mysql.com/doc/connector-python/en/)
- [vis-network Documentation](https://visjs.github.io/vis-network/docs/network/)
- [Bootstrap 5](https://getbootstrap.com/docs)
  
## 👨‍💻 Creator

Celia Victor [(Needlebrook)](https://github.com/Needlebrook)
