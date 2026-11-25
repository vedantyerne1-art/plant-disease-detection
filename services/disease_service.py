import json

from database.disease_db import get_connection


def _deserialize(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except json.JSONDecodeError:
        return [value]


def serialize_disease(row):
    return {
        "disease_id": row["disease_id"],
        "disease_name": row["disease_name"],
        "scientific_name": row["scientific_name"],
        "affected_plant": row["affected_plant"],
        "disease_category": row["disease_category"],
        "description": row["description"],
        "symptoms": _deserialize(row["symptoms"]),
        "causes": _deserialize(row["causes"]),
        "spread_mechanism": row["spread_mechanism"],
        "prevention": _deserialize(row["prevention"]),
        "treatment": _deserialize(row["treatment"]),
        "reference_sources": _deserialize(row["reference_sources"]),
        "last_verified_date": row["last_verified_date"],
    }


def get_disease(disease_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM diseases WHERE disease_id = ?",
            (disease_id,),
        ).fetchone()
    return serialize_disease(row) if row else None


def search_diseases(query="", category="", plant=""):
    conditions = []
    parameters = []
    if query:
        conditions.append("(disease_name LIKE ? OR affected_plant LIKE ?)")
        pattern = f"%{query}%"
        parameters.extend([pattern, pattern])
    if category:
        conditions.append("disease_category = ?")
        parameters.append(category)
    if plant:
        conditions.append("affected_plant = ?")
        parameters.append(plant)

    sql = "SELECT * FROM diseases"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY affected_plant, disease_name"

    with get_connection() as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [serialize_disease(row) for row in rows]
