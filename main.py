from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("DN_AIRFLOW")
password = os.getenv("DN_AIRFLOW_PASSWORD")
app = FastAPI()
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@10.10.12.181:5432/dataops')

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/convexhull")
def get_hull(time: int = Query(...)):
    with engine.connect() as conn:
        result = conn.execute(text("""
                SELECT json_agg(
                json_build_object(
                  'type', 'Feature',
                  'geometry', ST_AsGeoJSON(ST_Transform(m.live_station_geometry, 4326))::json,
                  'properties', json_build_object()
                    )
                ) AS features
                FROM 문재식.tb_metropolitan_morning_commute_od_202407 m
                JOIN (
                    SELECT ST_Buffer(
                               ST_Transform(
                                   ST_SetSRID(
                                       ST_MakePoint(126.976296, 37.563641), 4326), 5179
                               ),
                               300) AS geom
                ) b
                  ON ST_Within(m.work_station_geometry, b.geom)
                WHERE m.morning_commute_average_time < :time
        """), {"time": time})
        row = result.first()
        features = row[0] if row else []
        return JSONResponse(content={
            "type": "FeatureCollection",
            "features": features
        })

        return JSONResponse(content=json.loads(row[0]))
