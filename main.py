from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
import json
import os

user = 'dn_airflow'
password = 'N2xusA!rf!0w'
app = FastAPI()
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@10.10.12.181:5432/dataops')

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/convexhull")
def get_hull(time: int = Query(...)):
    with engine.connect() as conn:
        # 1. Hull geometry (예: concave hull도 동일!)
        hull_row = conn.execute(text("""
            WITH filtered AS (
                SELECT *,
                       ST_Distance(
                         ST_Transform(m.live_station_geometry, 4326),
                         ST_SetSRID(ST_MakePoint(126.976296, 37.563641), 4326)
                       ) AS dist
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
            ),
            no_outlier AS (
                SELECT *
                FROM filtered
                ORDER BY dist ASC
                LIMIT (SELECT GREATEST(COUNT(*) - 10, 0) FROM filtered)
            )
            SELECT ST_AsGeoJSON(
                     ST_Transform(
                       ST_ConvexHull(ST_Collect(no_outlier.live_station_geometry)), 4326
                     )
                   ) AS geojson
            FROM no_outlier;
        """), {"time": time}).first()
        hull_geojson = json.loads(hull_row[0]) if hull_row and hull_row[0] else None

        # 2. 모든 정류장 포인트
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
                  ON ST_Within(m.work_station_geometry, b.geom)
                WHERE m.morning_commute_average_time < :time
            )
            SELECT ST_AsGeoJSON(
                           ST_Transform(
                                   m.live_station_geometry, 4326)), 
                   m.live_station_name,
                    m.morning_commute_average_time,
                    m.morning_commute_median_time
            FROM filtered m
            ORDER BY m.morning_commute_average_distance DESC
            OFFSET 10 LIMIT 150 
            ;
        """), {"time": time}).fetchall()

        # 3. FeatureCollection 생성
        features = []
        # hull(폴리곤) feature 추가
        if hull_geojson:
            features.append({
                "type": "Feature",
                "geometry": hull_geojson,
                "properties": {"type": "hull"}
            })
        # 정류장 포인트 feature 추가
        for row in point_rows:
            if row[0]:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(row[0]),
                    "properties": {"type": "station",
                                   "name": row[1],
                                   "average_time" : row[2],
                                   "median_time" : row[3]}
                })

        return JSONResponse(content={
            "type": "FeatureCollection",
            "features": features
        })
