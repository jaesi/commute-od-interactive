from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
import json
from decimal import Decimal

def to_float_safe(value):
    return float(value) if isinstance(value, Decimal) else value

user = 'dn_airflow'
password = 'N2xusA!rf!0w'
app = FastAPI()
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@10.10.12.181:5432/dataops')

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/stations")
def get_stations():
    with engine.connect() as conn:
        point_rows = conn.execute(text("""
            WITH filtered AS (
                SELECT *
                FROM 문재식.tb_metropolitan_morning_commute_od_202407 m
                JOIN (
                    SELECT ST_Buffer(
                               ST_Transform(
                                   ST_SetSRID(
                                       ST_MakePoint(126.976296, 37.563641), 4326), 5179
                               ),
                               300) AS geom
                ) b
                  ON ST_Within(m.work_station_geometry, b.geom))
            SELECT ST_AsGeoJSON(
                           ST_Transform(
                                   m.live_station_geometry, 4326)), 
                   m.live_station_name,
                   m.morning_commute_average_time,
                   m.morning_commute_median_time,
                   m.morning_commute_average_distance,
                   m.morning_commute_median_distance,
                m.morning_daily_commute_count
            FROM filtered m;
        """)).fetchall()

        # FeatureCollection 생성 (포인트만)
        features = []
        for row in point_rows:
            if row[0]:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(row[0]),
                    "properties": {
                        "type": "station",
                        "name": row[1],
                        "average_time": row[2],
                        "median_time": row[3],
                        "average_distance": row[4],
                        "median_distance": row[5],
                        "commute_count": to_float_safe(row[6])
                    }
                })

        return JSONResponse(content={
            "type": "FeatureCollection",
            "features": features
        })