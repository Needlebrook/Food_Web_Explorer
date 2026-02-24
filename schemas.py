from pydantic import BaseModel
from typing import List

class Node(BaseModel):
    id: int
    common_name: str
    scientific_name: str
    trophic_level: str

class Edge(BaseModel):
    from_id: int
    to: int
    feed_type: str

class FoodWeb(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
