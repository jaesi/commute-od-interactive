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
        result = conn.execute(text("""
                                   WITH filtered AS (SELECT *,
                                                            ST_Distance(
                                                                    ST_Transform(m.live_station_geometry, 4326),
                                                                    ST_SetSRID(ST_MakePoint(126.976296, 37.563641), 4326)
                                                            ) AS dist
                                                     FROM 문재식.tb_metropolitan_morning_commute_od_202407 m
                                                              JOIN (SELECT ST_Buffer(
                                                                                   ST_Transform(
                                                                                           ST_SetSRID(
                                                                                                   ST_MakePoint(126.976296, 37.563641),
                                                                                                   4326), 5179
                                                                                   ),
                                                                                   300) AS geom) b
                                                                   ON ST_Within(m.work_station_geometry, b.geom)
                                                     WHERE m.morning_commute_average_time < :time),
                                        no_outlier AS (SELECT *
                                                       FROM filtered
                                                       ORDER BY dist ASC
                                                       OFFSET 0 LIMIT (SELECT GREATEST(COUNT(*) - 10, 0) FROM filtered)
                                            -- 전체 중에서 가장 먼 10개만 버리고 나머지
                                        )
                                   SELECT ST_AsGeoJSON(
                                                  ST_Transform(
                                                          ST_ConvexHull(ST_Collect(no_outlier.live_station_geometry)),
                                                          4326
                                                  )
                                          ) AS geojson
                                   FROM no_outlier;
                                   """), {"time": time})
        row = result.first()
        if not row or not row[0]:
            return JSONResponse(content={
                "type": "Polygon",
                "coordinates": []
            })
        return JSONResponse(content=json.loads(row[0]))
