
import json

input_file = '/home/fenix3819/amantti-weather-service/frontend/public/colombia_depto.json'
output_file = '/home/fenix3819/amantti-weather-service/frontend/public/antioquia_depto.geojson'

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter for Antioquia (DPTO code "05")
filtered_features = [
    feature for feature in data['features']
    if feature['properties'].get('DPTO') == "05"
]

data['features'] = filtered_features

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Filtered {len(filtered_features)} feature(s) for Antioquia department.")
