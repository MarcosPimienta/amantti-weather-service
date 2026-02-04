
import json

with open('/home/fenix3819/amantti-weather-service/frontend/public/antioquia.geojson', 'r') as f:
    data = json.load(f)

names = sorted([f['properties']['NOMBRE_MPI'] for f in data['features']])
print("\n".join(names))
