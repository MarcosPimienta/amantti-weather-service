<script setup lang="ts">
import { onMounted, ref, watch } from 'vue' // 📍 Added watch
import WeatherOverlay from '../WeatherOverlay.vue'
import {
  Viewer,
  createWorldTerrainAsync,
  Ion,
  Color,
  SkyAtmosphere,
  Cartesian3,
  JulianDate,
  GeoJsonDataSource,
  PolylineGraphics,
  ColorMaterialProperty,
  ConstantProperty,
  Cartographic,
  Math as CesiumMath,
  PolygonHierarchy,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  defined,
  type Entity,
  CustomDataSource, 
  BoxGraphics, 
  BoundingSphere, 
  HeightReference,
  ImageMaterialProperty,
  MaterialProperty,
  ParticleSystem,
  BoxEmitter,
  Cartesian2,
  Transforms,
  Matrix3,
  Matrix4,
  Cartesian4,
  UrlTemplateImageryProvider,
  CloudCollection,
  ProviderViewModel,
  VerticalOrigin,
  EllipsoidGraphics,
  Quaternion,
  HeadingPitchRoll,
  Matrix2
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const cesiumContainer = ref<HTMLElement | null>(null)
const selectedLocation = ref<{ name: string; lat: number; lon: number; alt: number } | null>(null)
const currentWeatherMode = ref<string[]>(['clear']) // Default mode
const currentWeatherData = ref<{ temp: number; rain: number; humidity: number } | null>(null)
// Store local polygon positions for the emitter
const currentLocalPolygon = ref<{ x: number, y: number }[]>([]); 
// Store local bounding box
const currentLocalBounds = ref<{ minX: number, maxX: number, minY: number, maxY: number }>({ minX: 0, maxX: 0, minY: 0, maxY: 0 });
const currentPolygonCenter = ref<Cartesian3 | null>(null);

// Viewer instance accessible 
let cesiumViewer: Viewer | null = null

// Rain System
let rainSystem: ParticleSystem | null = null


// Data Source for 3D Bars
let barDataSource: CustomDataSource | null = null
let fogDataSource: CustomDataSource | null = null // 🌫️ Fog Polygons
let municipalitiesDataSource: GeoJsonDataSource | null = null // 📍 Added reliable reference
let cloudCollection: CloudCollection | null = null; // ☁️ Clouds

// Mock Data Cache to keep values consistent
const townDataCache: Record<string, { temp: number, rain: number, humidity: number }> = {}

const getTownData = (townName: string) => {
    if (!townDataCache[townName]) {
        // First determine if there's rain (30% chance)
        const hasRain = Math.random() < 0.3;
        
        let temp, humidity, rain;
        
        if (hasRain) {
            // 🌧️ Rainy: High Humidity, Cooler Temp
            temp = 16 + Math.random() * 6; // 16-22°C
            humidity = 85 + Math.random() * 15; // 85-100%
            rain = 5 + Math.random() * 45; // 5-50 mm
        } else {
            // No Rain: depends on randomness
            const isHot = Math.random() > 0.5;
            
            if (isHot) {
                 // ☀️ Hot & Dry
                 temp = 26 + Math.random() * 9; // 26-35°C
                 humidity = 30 + Math.random() * 30; // 30-60%
            } else {
                 // ☁️ Cool & Humid (Foggy potentially)
                 temp = 18 + Math.random() * 6; // 18-24°C
                 humidity = 80 + Math.random() * 20; // Force high humidity (80-100%) for visibility debug
            }
            rain = 0;
        }
        
        townDataCache[townName] = { temp, rain, humidity };
    }
    return townDataCache[townName];
}

const handleLayerSwitch = (layerName: string) => {
    if (!cesiumViewer || !cesiumViewer.baseLayerPicker) return
    
    const models = cesiumViewer.baseLayerPicker.viewModel.imageryProviderViewModels
    let target = models.find((vm: any) => vm.name === layerName)
    if (!target && layerName.includes('Bing')) {
        target = models.find((vm: any) => vm.name.includes('Bing Maps Aerial'))
    }
    if (target) {
        cesiumViewer.baseLayerPicker.viewModel.selectedImagery = target
    }
}

const interpolateColor = (color1: string, color2: string, factor: number) => {
    // Simple RGB interpolation
    const c1 = Color.fromCssColorString(color1);
    const c2 = Color.fromCssColorString(color2);
    const result = Color.lerp(c1, c2, factor, new Color());
    return result.toCssColorString();
}

// 📐 Geometry Helpers
const pointInPolygon = (point: { x: number, y: number }, vs: { x: number, y: number }[]) => {
    // Ray-casting algorithm based on the Jordan Curve Theorem
    let x = point.x, y = point.y;
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        const p1 = vs[i];
        const p2 = vs[j];

        if (!p1 || !p2) continue;

        let xi = p1.x, yi = p1.y;
        let xj = p2.x, yj = p2.y;
        
        let intersect = ((yi > y) !== (yj > y))
            && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
};

const computeLocalPolygon = (positions: Cartesian3[], center: Cartesian3) => {
    // 1. Compute Local Frame (ENU) at Center
    const toFixed = Transforms.eastNorthUpToFixedFrame(center);
    const toLocal = Matrix4.inverse(toFixed, new Matrix4());
    
    // 2. Transform all points to Local Frame
    const localPoints: { x: number, y: number }[] = [];
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    for (const pos of positions) {
        const localPos = Matrix4.multiplyByPoint(toLocal, pos, new Cartesian3());
        // Z should be approx 0 if points are on surface and center is on surface.
        // We only care about XY for the particle emitter check.
        localPoints.push({ x: localPos.x, y: localPos.y });
        
        if (localPos.x < minX) minX = localPos.x;
        if (localPos.x > maxX) maxX = localPos.x;
        if (localPos.y < minY) minY = localPos.y;
        if (localPos.y > maxY) maxY = localPos.y;
    }
    
    return { polygon: localPoints, bounds: { minX, maxX, minY, maxY } };
}

// Custom Emitter Class
class PolygonEmitter {
    private _polygon: { x: number, y: number }[];
    private _bounds: { minX: number, maxX: number, minY: number, maxY: number };
    private _minZ: number;
    private _maxZ: number;

    constructor(polygon: { x: number, y: number }[], bounds: any, minZ: number = -4000.0, maxZ: number = 0.0) {
        this._polygon = polygon;
        this._bounds = bounds;
        this._minZ = minZ;
        this._maxZ = maxZ;
    }

    emit(particle: any, dt: number) {
        // Rejection Sampling
        // Try up to 10 times to find a point inside the polygon
        for (let i = 0; i < 10; i++) {
            const x = CesiumMath.randomBetween(this._bounds.minX, this._bounds.maxX);
            const y = CesiumMath.randomBetween(this._bounds.minY, this._bounds.maxY);
            
            if (pointInPolygon({ x, y }, this._polygon)) {
                // Found a valid spot!
                particle.position.x = x;
                particle.position.y = y;
                // Spawn randomly in the vertical column 
                particle.position.z = CesiumMath.randomBetween(this._minZ, this._maxZ); 
                
                particle.velocity.x = 0;
                particle.velocity.y = 0;
                particle.velocity.z = -10.0; // Initial speed
                
                return; // Success
            }
        }
        // If we fail 10 times, kill the particle but ensure it has valid data to prevent crashes
        particle.life = 0.0; 
        particle.position.x = this._bounds.minX;
        particle.position.y = this._bounds.minY;
        particle.position.z = this._minZ;
        particle.velocity.x = 0;
        particle.velocity.y = 0;
        particle.velocity.z = -1.0; // Non-zero just in case
    }
}

const createRainCanvas = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    ctx.fillStyle = 'rgba(255, 255, 255, 0)';
    ctx.fillRect(0, 0, 32, 32);

    ctx.fillStyle = 'rgba(220, 230, 255, 0.8)';
    ctx.beginPath();
    ctx.moveTo(14, 0);
    ctx.lineTo(18, 0);
    ctx.lineTo(16, 32);
    ctx.fill();
    
    return canvas;
}



const currentRainRadius = ref(1500.0);

const refreshRainEffect = () => {
    if (!cesiumViewer) return;
    
    // Always remove existing first to handle updates
    if (rainSystem) {
        cesiumViewer.scene.primitives.remove(rainSystem);
        rainSystem = null;
    }
    
    const location = selectedLocation.value;
    const data = currentWeatherData.value;
    
    // Conditions to show rain/clouds:
    // 1. Location selected
    // 2. Data available 
    if (!location || !data) {
        return;
    }

    // Rain Logic
    if (data.rain > 0 && currentWeatherMode.value.includes('rain')) {
         // Use the Polygon Center if available (for precise alignment), otherwise fallback to location (click point)
        let position: Cartesian3;
        if (currentPolygonCenter.value) {
            // We need to add height to the center.
            // Convert to Cartographic to add altitude safely
            const carto = Cartographic.fromCartesian(currentPolygonCenter.value);
            position = Cartesian3.fromRadians(carto.longitude, carto.latitude, location.alt + 4000); 
        } else {
            position = Cartesian3.fromDegrees(location.lon, location.lat, location.alt + 4000); 
        }

        const modelMatrix = Transforms.eastNorthUpToFixedFrame(position);
        
        // Scale intensity
        const emissionRate = Math.min(Math.max(data.rain * 2, 5), 100); 
        const speed = 10.0;
        const radius = currentRainRadius.value;

        rainSystem = new ParticleSystem({
            image: createRainCanvas(),
            startColor: Color.WHITE.withAlpha(0.6),
            endColor: Color.WHITE.withAlpha(0.0),
            startScale: 1.0,
            endScale: 1.0,
            minimumParticleLife: 60.0, 
            maximumParticleLife: 60.0,
            minimumSpeed: speed * 0.8,
            maximumSpeed: speed * 1.2,
            imageSize: new Cartesian2(6, 20),
            emissionRate: emissionRate,
            // Use our custom PolygonEmitter if available, else fallback
            emitter: (currentLocalPolygon.value.length > 0) 
                ? new PolygonEmitter(currentLocalPolygon.value, currentLocalBounds.value)
                : new BoxEmitter(new Cartesian3(radius * 1.4, radius * 1.4, 4000.0)),
            lifetime: 16.0,
            modelMatrix: modelMatrix,
            updateCallback: (particle: any, dt: number) => {
               particle.velocity.z = -speed; 
               particle.velocity.x = 0;
               particle.velocity.y = 0;
            }
        });
        
        cesiumViewer.scene.primitives.add(rainSystem);
    }
}

// ☁️ Cloud Settings (Reactive)
const cloudSettings = ref({
    maxSizeX: 25000,
    maxSizeY: 15000,
    maxSizeZ: 5000,
    textureScale: 20, 
    slice: 0.5,
    brightness: 1.0,
    altitude: 5000,
    count: 30
});

const refreshCloudEffect = () => {
    if (!cesiumViewer) return;

    if (cloudCollection) {
        cesiumViewer.scene.primitives.remove(cloudCollection);
        cloudCollection = null;
    }

    const location = selectedLocation.value;
    const data = currentWeatherData.value;

    if (!location || !data) return;

    // Debug logs
    console.log(`[CloudDebug] Refreshing. Mode: ${currentWeatherMode.value}, Data:`, data);
    console.log(`[CloudDebug] Settings:`, cloudSettings.value);

    // Show clouds on rain or if humidity is high
    if (currentWeatherMode.value.includes('rain') || (currentWeatherMode.value.includes('humidity') && data.humidity > 60)) {
         cloudCollection = new CloudCollection({
             noiseDetail: 16.0, // Fixed detail for Cumulus
             noiseOffset: Math.random() * 1000.0
         });

         const count = cloudSettings.value.count;
         console.log(`[CloudDebug] Spawning ${count} clouds...`);

        if (currentPolygonCenter.value && currentLocalPolygon.value.length > 0) {
             const center = currentPolygonCenter.value;
             const toFixed = Transforms.eastNorthUpToFixedFrame(center);
             const bounds = currentLocalBounds.value;
             const polygon = currentLocalPolygon.value;
             
             let added = 0;
             let attempts = 0;
             const maxAttempts = count * 20; 
             
             while (added < count && attempts < maxAttempts) {
                 const x = CesiumMath.randomBetween(bounds.minX, bounds.maxX);
                 const y = CesiumMath.randomBetween(bounds.minY, bounds.maxY);
                 
                 if (pointInPolygon({x, y}, polygon)) {
                     // Inside!
                     const z = CesiumMath.randomBetween(cloudSettings.value.altitude - 500, cloudSettings.value.altitude + 500); 
                     
                     const localPos = new Cartesian3(x, y, z);
                     const worldPos = Matrix4.multiplyByPoint(toFixed, localPos, new Cartesian3());
                     
                     // ☁️ Cumulus Cloud Properties
                     const maxWidth = cloudSettings.value.maxSizeX;
                     const maxLength = cloudSettings.value.maxSizeY;
                     const maxHeight = cloudSettings.value.maxSizeZ;
                     
                     // Randomize slightly based on max size
                     const sizeX = maxWidth * (0.8 + Math.random() * 0.4);
                     const sizeY = maxLength * (0.8 + Math.random() * 0.4);
                     const sizeZ = maxHeight * (0.8 + Math.random() * 0.4);
                     
                     const texScale = cloudSettings.value.textureScale;

                     cloudCollection.add({
                         position: worldPos,
                         scale: new Cartesian2(texScale, texScale), 
                         maximumSize: new Cartesian3(sizeX, sizeY, sizeZ), 
                         slice: cloudSettings.value.slice, 
                         brightness: cloudSettings.value.brightness 
                     });

                     added++;
                 }
                 attempts++;
             }
             console.log(`[CloudDebug] Polygon Spawn: Added ${added} clouds.`);
         } else {
             // Fallback for no polygon
             const center = Cartesian3.fromDegrees(location.lon, location.lat, location.alt + cloudSettings.value.altitude);
             const spread = 20000; 

             for (let i = 0; i < count; i++) {
                 const x = center.x + (Math.random() - 0.5) * spread;
                 const y = center.y + (Math.random() - 0.5) * spread;
                 const z = center.z + (Math.random() - 0.5) * 1000;

                 cloudCollection.add({
                     position: new Cartesian3(x, y, z),
                     scale: new Cartesian2(cloudSettings.value.textureScale, cloudSettings.value.textureScale),
                     maximumSize: new Cartesian3(cloudSettings.value.maxSizeX, cloudSettings.value.maxSizeY, cloudSettings.value.maxSizeZ),
                     slice: cloudSettings.value.slice,
                     brightness: cloudSettings.value.brightness
                 });
             }
         }
         
         cesiumViewer.scene.primitives.add(cloudCollection);
    }
}

const updateCloudSettings = (newSettings: any) => {
    Object.assign(cloudSettings.value, newSettings);
    refreshCloudEffect();
};



// ------------------------------------------------------------------
// 🌡️ Create Shape-Based Temperature Gradient (Inner Glow)
// ------------------------------------------------------------------
// Helper: Get Color from Heatmap Scale (0..1)
const getHeatmapColor = (t: number): [number, number, number] => {
    // 0.0: Blue (0, 0, 255)
    // 0.25: Cyan (0, 255, 255)
    // 0.5: Green (0, 255, 0)
    // 0.75: Yellow (255, 255, 0)
    // 1.0: Red (255, 0, 0)

    t = Math.max(0, Math.min(1, t));

    if (t < 0.25) {
        // Blue -> Cyan
        const localT = t / 0.25;
        return [0, Math.floor(localT * 255), 255];
    } else if (t < 0.5) {
        // Cyan -> Green
        const localT = (t - 0.25) / 0.25;
        return [0, 255, Math.floor(255 * (1 - localT))];
    } else if (t < 0.75) {
        // Green -> Yellow
        const localT = (t - 0.5) / 0.25;
        return [Math.floor(localT * 255), 255, 0];
    } else {
        // Yellow -> Red
        const localT = (t - 0.75) / 0.25;
        return [255, Math.floor(255 * (1 - localT)), 0];
    }
}

const createShapeGradient = (positions: Cartesian3[], center: Cartesian3, temp: number, maxTemp: number = 35) => {
    // 1. Get Local 2D Polygon (normalized 0..1 relative to bounds)
    // We reuse the logic but need to map to canvas 0..512 ignoring aspect ratio (Cesium handles UV stretch)
    
    const { polygon, bounds } = computeLocalPolygon(positions, center);
    
    const canvas = document.createElement('canvas');
    const size = 256; // Smaller texture is faster and sufficient for blur
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return canvas;

    // Map bounds to full canvas size (0..size) to utilize resolution
    const width = bounds.maxX - bounds.minX;
    const height = bounds.maxY - bounds.minY;
    
    // Draw Polygon in White
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    polygon.forEach((p, i) => {
        // Normalize 0..1 then scale to size
        // Note: Y might need flip? Usually Cesium UV (0,0) is bottom-left? 
        // Let's just draw standard. If inverted, we can flip Y here.
        // Assuming standard canvas coordinates.
        const x = ((p.x - bounds.minX) / width) * size;
        const y = size - (((p.y - bounds.minY) / height) * size); // Flip Y to match Bottom-Up UV?
        
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fill();

    // Apply Blur to create "Distance Field"
    // We can't use CSS filter easily on offscreen canvas in all browsers, but ctx.filter works in modern ones
    // Or we can just draw it multiple times with offsets? 
    // Simplest: use ctx.filter
    
    const tempRatio = Math.min(Math.max(temp / maxTemp, 0), 1);
    
    // Create a generic "Heat" map from the shape
    // We want the center to be 1.0, edge to be 0.0
    // The blur spreads the white out. We want "Inset" blur.
    
    // Better approach for "Inner Glow":
    // 1. Clear.
    // 2. Draw Polygon (Clip).
    // 3. Draw a Shadow or Blur INSIDE?
    // Hard to do "Inset Blur".
    
    // Pixel Processing Approach:
    // 1. Draw White Polygon.
    // 2. Apply Heavy Blur.
    // 3. Mask with Original Polygon (Sharp).
    // This gives soft edges inside, sharp edges outside.
    
    // Customize Colors: "Spatial Heatmap"
    // The glow radiates from the center, following the shape contours.
    // The color at any point represents a "local temperature" in that gradient field.
    // Center = Actual Temp. Edge = Cooler Base Temp.
    
    // Base Temp for the edge of the glow (e.g., 20°C seems reasonable as a "cool" floor)
    // Or relative? Let's say Edge is 0 value, Center is 1 value.
    // We map Value to Color Ramp based on (Top Temp / Max Global Temp).
    
    // Get Data
    const imgData = ctx.getImageData(0, 0, size, size);
    const data = imgData.data;
    
    // Intensity (Alpha/White) determines "Distance from Edge"
    for (let i = 0; i < data.length; i += 4) {
        const intensity = data[i + 3] ?? 0; // Alpha channel (from blur)
        
        if (intensity < 10) {
             data[i + 3] = 0; // Transparent outside
             continue;
        }
        
        const alpha = intensity / 255; // 0..1 (1 = Center/Thick, 0 = Edge)
        
        // Non-Linear map to push the "hot" values towards the center visually
        // t represents normalized position in the gradient (0 = Edge, 1 = Center)
        const t = Math.pow(alpha, 1.2); 
        
        // Calculate "Effective Temperature Ratio" for this pixel
        // Center reaches 'tempRatio'. Edge starts at 0 (Deep Blue).
        const pixelRatio = t * tempRatio; 
        
        // Get Color for this ratio
        const [rVal, gVal, bVal] = getHeatmapColor(pixelRatio);

        data[i] = rVal;
        data[i + 1] = gVal;
        data[i + 2] = bVal;

        // Alpha: heavily fade edges, keep center relatively opaque
        data[i + 3] = Math.max(0, Math.floor(t * 180)); 
    }
    
    // Put back
    ctx.putImageData(imgData, 0, 0);
    
    // FINAL PASS: Clip to sharp polygon to remove outside blur
    // To do this, we need to draw the polygon again as a mask?
    // Composite 'destination-in' with sharp polygon?
    
    const finalCanvas = document.createElement('canvas');
    finalCanvas.width = size;
    finalCanvas.height = size;
    const fCtx = finalCanvas.getContext('2d');
    if (!fCtx) return canvas;
    
    // Draw Blurred Image
    fCtx.drawImage(canvas, 0, 0);
    
    // Mask with Sharp Polygon
    fCtx.globalCompositeOperation = 'destination-in';
    fCtx.beginPath();
    polygon.forEach((p, i) => {
        const x = ((p.x - bounds.minX) / width) * size;
        const y = size - (((p.y - bounds.minY) / height) * size);
        if (i === 0) fCtx.moveTo(x, y);
        else fCtx.lineTo(x, y);
    });
    fCtx.closePath();
    fCtx.fill();
    
    return finalCanvas;
}


// ------------------------------------------------------------------
// 🏷️ Create Widget Canvas (Floating Card)
// ------------------------------------------------------------------
const createWidgetCanvas = (townName: string, data: any) => {
    const canvas = document.createElement('canvas');
    const w = 256;
    const h = 128;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;
    
    // Background: Dark Glass
    ctx.fillStyle = 'rgba(20, 20, 40, 0.85)';
    ctx.beginPath();
    // Rounded rect
    const r = 16;
    ctx.roundRect(10, 10, w - 20, h - 20, r);
    ctx.fill();
    
    // Border: Neon Cyan
    ctx.strokeStyle = '#00FFFF';
    ctx.lineWidth = 4;
    ctx.stroke();
    
    // Text: Town Name
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 20px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(townName.toUpperCase(), w/2, 40);
    
    // Icon (Emoji for now)
    const isRain = data.rain > 0;
    const emoji = isRain ? '🌧️' : '☀️';
    ctx.font = '50px sans-serif';
    ctx.fillText(emoji, 60, 95);
    
    // Weather Data
    ctx.textAlign = 'left';
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 36px monospace';
    ctx.fillText(`${data.temp.toFixed(0)}°`, 110, 80);
    
    ctx.font = '16px monospace';
    ctx.fillStyle = '#AAAAAA';
    
    if (isRain) {
        ctx.fillText(`${data.rain.toFixed(1)}mm`, 110, 100);
    } else {
        ctx.fillText(`Clear`, 110, 100);
    }
    
    return canvas;
}

const createFogCanvas = (humidity: number) => {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    // Base transparency driven by humidity (40-100)
    // Map 40 -> 0.0, 100 -> 0.9
    const intensity = Math.max(0, Math.min((humidity - 40) / 60, 1));
    // If humidity is low, fog is invisible
    if (intensity <= 0) return canvas;

    const baseAlpha = 0.3 + (intensity * 0.5); // 0.3 to 0.8

    // Clear
    ctx.clearRect(0, 0, 512, 512);

    // Create softer, more layered fog
    const particles = 80;
    
    for (let i = 0; i < particles; i++) {
        const x = Math.random() * 512;
        const y = Math.random() * 512;
        const r = 40 + Math.random() * 120; // Larger puffs
        
        // Non-uniform scaling for wisps
        ctx.save();
        ctx.translate(x, y);
        ctx.scale(1 + Math.random(), 1 + Math.random());
        
        const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
        grad.addColorStop(0, `rgba(240, 245, 255, ${0.08 * baseAlpha})`); // Very faint core
        grad.addColorStop(0.5, `rgba(230, 240, 255, ${0.04 * baseAlpha})`); 
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
    
    // Overall wash
    ctx.fillStyle = `rgba(220, 230, 245, ${0.1 * baseAlpha})`;
    ctx.fillRect(0,0,512,512);

    return canvas;
}

const createDomeFogTexturedMaterial = (humidity: number) => {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    // Clear
    ctx.clearRect(0, 0, size, size);

    // 🌫️ Volumetric Dome Texture
    // Radial Gradient: White center -> Transparent edge
    const cx = size / 2;
    const cy = size / 2;
    const radius = size / 2;

    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    
    // Intensity based on humidity
    // 0.3 min opacity + up to 0.5 more based on humidity
    const intensity = Math.max(0.3, Math.min((humidity - 20) / 80, 1)); 
    const centerAlpha = 0.6 + (intensity * 0.4); // 0.6 to 1.0

    gradient.addColorStop(0, `rgba(255, 255, 255, ${centerAlpha})`);   // Core
    gradient.addColorStop(0.4, `rgba(245, 250, 255, ${centerAlpha * 0.8})`); 
    gradient.addColorStop(0.7, `rgba(240, 245, 255, ${centerAlpha * 0.4})`);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)'); // Edge

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);

    // Add some noise for "fluffiness"
    const particles = 200;
    for (let i = 0; i < particles; i++) {
        const x = Math.random() * size;
        const y = Math.random() * size;
        const r = 20 + Math.random() * 60;
        
        // Only draw if inside circle roughly
        const d = Math.sqrt((x-cx)*(x-cx) + (y-cy)*(y-cy));
        if (d > radius) continue;

        ctx.save();
        ctx.translate(x, y);
        const pGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
        pGrad.addColorStop(0, `rgba(255, 255, 255, ${0.15 * centerAlpha})`);
        pGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        
        ctx.fillStyle = pGrad;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    return canvas;
}

const computeOrientedBounds = (positions: Cartesian3[], center: Cartesian3) => {
    // 1. Compute Local Frame (ENU) at Center
    const toFixed = Transforms.eastNorthUpToFixedFrame(center);
    const toLocal = Matrix4.inverse(toFixed, new Matrix4());
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    for (const pos of positions) {
        const localPos = Matrix4.multiplyByPoint(toLocal, pos, new Cartesian3());
        
        if (localPos.x < minX) minX = localPos.x;
        if (localPos.x > maxX) maxX = localPos.x;
        if (localPos.y < minY) minY = localPos.y;
        if (localPos.y > maxY) maxY = localPos.y;
    }
    
    const width = maxX - minX;
    const height = maxY - minY;
    
    // Local Center of the Bounds (midpoint of min/max)
    // Note: This center might be slightly offset from the polygon centroid (input 'center')
    const localCenter = new Cartesian3(
        (minX + maxX) / 2, 
        (minY + maxY) / 2, 
        0.0 
    );
    
    // Transform local center back to World Fixed Frame
    const boundsCenter = Matrix4.multiplyByPoint(toFixed, localCenter, new Cartesian3());
    
    // Orientation: Just the ENU frame orientation
    // Extract rotation matrix from 'toFixed' transform
    const rotationMatrix = new Matrix3();
    Matrix4.getMatrix3(toFixed, rotationMatrix);
    const rotation = Quaternion.fromRotationMatrix(rotationMatrix);
    
    return {
        center: boundsCenter,
        rotation: rotation,
        width: width,
        height: height
    };
}

const renderWeatherWidgets = async () => {
    if (!cesiumViewer || !barDataSource || !fogDataSource) return;
    
    barDataSource.entities.removeAll();
    fogDataSource.entities.removeAll();

    // 🔒 Filter: Only show if a location is selected
    if (!selectedLocation.value) return;

    const activeModes = currentWeatherMode.value;
    
    if (!municipalitiesDataSource) return;

    const entities = municipalitiesDataSource.entities.values;

    // Reset loop
    for (let i = 0; i < entities.length; i++) {
        const entity = entities[i];
        if (!entity?.polygon) continue;
        
        const rawName = entity.properties?.NOMBRE_MPI?.getValue();
        if (!rawName) continue;
        
        // Reset Base Polygon to default first
        entity.polygon.material = new ColorMaterialProperty(Color.CYAN.withAlpha(0.05));
        
        if (rawName !== selectedLocation.value.name) continue;

        const data = getTownData(rawName);

        // Calculate Centroid & Hierarchy
        let center: Cartesian3 | null = null;
        let positions: Cartesian3[] = [];
        let hierarchy: any = null;

        hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer.clock.currentTime);
        if (hierarchy) {
             positions = hierarchy.positions;
             const boundingSphere = BoundingSphere.fromPoints(positions);
             center = boundingSphere.center;
        }
        
        if (!center) continue;

        // 1. Base Layer: Temperature (Clear Mode) - Inner Glow
        if (activeModes.includes('clear')) {
             const material = new ImageMaterialProperty({
                  image: createShapeGradient(positions, center, data.temp, 40), 
                  transparent: true
             });
             entity.polygon.material = material;
        }

        // 2. Fog Layer: Humidity/Rain Mode - "Oriented Fog Dome"
        if (activeModes.includes('humidity') || activeModes.includes('rain')) {
             if (hierarchy) {
                 const bounds = computeOrientedBounds(positions, center);
                 
                 // Radius of the ellipsoid
                 // Use 1/2 width and height since radii are half-axes
                 const radiusX = bounds.width * 0.55;  // Slightly larger than half-width to cover corners
                 const radiusY = bounds.height * 0.55; 
                 
                 // Height: Proportional to the average size, but flattened
                 const avgSize = (radiusX + radiusY) / 2;
                 const height = avgSize * 0.5; 

                 fogDataSource.entities.add({
                     position: bounds.center,
                     orientation: bounds.rotation,
                     ellipsoid: new EllipsoidGraphics({
                         radii: new Cartesian3(radiusX, radiusY, height),
                         material: new ImageMaterialProperty({
                             image: createDomeFogTexturedMaterial(data.humidity),
                             transparent: true
                         }),
                     })
                 });
             }
        }

        // 3. Floating Widget
        if (activeModes.length > 0) {
            barDataSource.entities.add({
                 position: center, // Centroid
                 billboard: {
                     image: createWidgetCanvas(rawName, data),
                     scale: 1.0,
                     pixelOffset: new Cartesian2(0, -100), // Float up
                     verticalOrigin: VerticalOrigin.BOTTOM,
                     disableDepthTestDistance: Number.POSITIVE_INFINITY, 
                     heightReference: HeightReference.RELATIVE_TO_GROUND
                 }
             });
        }
    }
}

const handleWeatherMode = (modes: string[]) => {
    currentWeatherMode.value = modes;
    refreshRainEffect();
    refreshCloudEffect(); 
    renderWeatherWidgets();
}

// 👀 Watch for Selection Changes
watch(selectedLocation, (newLoc) => {
    if (newLoc) {
        const data = getTownData(newLoc.name);
        currentWeatherData.value = data;

        if (municipalitiesDataSource) {
             const entities = municipalitiesDataSource.entities.values;
             const normalize = (str: string) => str.toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
             
             const entity = entities.find(e => {
                 const raw = e.properties?.NOMBRE_MPI?.getValue();
                 return raw && normalize(raw) === normalize(newLoc.name);
             });

             if (entity && entity.polygon && cesiumViewer) {
                 const hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer.clock.currentTime);
                 if (hierarchy) {
                     const bs = BoundingSphere.fromPoints(hierarchy.positions);
                     currentRainRadius.value = bs.radius * 0.9; 
                     currentPolygonCenter.value = bs.center; 
                     
                     const localPoly = computeLocalPolygon(hierarchy.positions, bs.center);
                     currentLocalPolygon.value = localPoly.polygon;
                     currentLocalBounds.value = localPoly.bounds;
                 }
             } else {
                currentRainRadius.value = 1500.0;
                currentLocalPolygon.value = [];
                currentPolygonCenter.value = null;
             }
        }
    } else {
        currentWeatherData.value = null;
        currentPolygonCenter.value = null;
    }
    refreshRainEffect();
    refreshCloudEffect();
    renderWeatherWidgets();
})

const resetCamera = () => {
    if (cesiumViewer) {
        cesiumViewer.camera.flyTo({
            destination: Cartesian3.fromDegrees(-75.5, 6.5, 500000), // Approximate center of Antioquia
            duration: 2,
        })
        selectedLocation.value = null // Optional: Deselect town on reset?
    }
}

onMounted(async () => {
  if (cesiumContainer.value) {
    Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN

    // 🗺️ Configure Imagery Provider (Default to Stadia or CartoDB Dark Matter)
    const stadiaApiKey = import.meta.env.VITE_STADIA_API_KEY
    let imageryProvider: UrlTemplateImageryProvider

    // Always try to use Stadia (with or without API key), in both DEV and PROD as requested
    if (stadiaApiKey) {
      // Use Stadia Maps with API key for best quality
      imageryProvider = new UrlTemplateImageryProvider({
        url: `https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}.png?api_key=${stadiaApiKey}`,
        credit: '© Stadia Maps © OpenMapTiles © OpenStreetMap contributors'
      })
      console.log('Using Stadia Maps with API key (PROD)')
    } else {
        // Fallback: Use CartoDB Dark Matter (often free for dev, good dark alternative)
        imageryProvider = new UrlTemplateImageryProvider({
            url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            credit: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: ['a', 'b', 'c', 'd']
        })
        console.log('Using CartoDB Dark Matter (Fallback for Stadia)')
    }
    // Note: If no API key, Cesium will use its default imagery (Bing)
    // User can manually switch to Stadia via base layer picker if using Cesium Ion

    // Assign to top-level variable
    cesiumViewer = new Viewer(cesiumContainer.value, {
      terrainProvider: await createWorldTerrainAsync({}),
      // @ts-ignore
      imageryProvider: imageryProvider, // 🗺️ Use Stadia (or default if null)
      timeline: false,
      animation: false, // ❌ Disable Animation Dial
      infoBox: false,
      selectionIndicator: false,
      // ❌ Disable Default Widgets (Top Right)
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      baseLayerPicker: true, // ✅ Keep enabled for manual switching
    })

    // Set custom imagery provider if Stadia API key is available
    // Set custom imagery provider
    if (imageryProvider) {
      cesiumViewer.imageryLayers.removeAll()
      cesiumViewer.imageryLayers.addImageryProvider(imageryProvider)

      // 📌 Add to BaseLayerPicker so switching works
      // We name it "Stadia Alidade Smooth Dark" to match WeatherOverlay logic
      const darkViewModel = new ProviderViewModel({
          name: 'Stadia Alidade Smooth Dark',
          tooltip: 'Dark Map Style',
          iconUrl: 'https://raw.githubusercontent.com/CesiumGS/cesium/master/Apps/Sandcastle/images/3.jpg', // Placeholder icon
          creationFunction: () => imageryProvider
      })

      // Add to list and select it
      if (cesiumViewer.baseLayerPicker) {
          const viewModel = cesiumViewer.baseLayerPicker.viewModel
          viewModel.imageryProviderViewModels.push(darkViewModel)
          viewModel.selectedImagery = darkViewModel
      }
    }

    if (cesiumViewer.scene) {
        // ... (existing scene setup) ... 
        
        // 📊 Add Custom Data Source for Bars
        barDataSource = new CustomDataSource('bars');
        cesiumViewer.dataSources.add(barDataSource);

        // 🌫️ Add Data Source for Fog
        fogDataSource = new CustomDataSource('fog');
        cesiumViewer.dataSources.add(fogDataSource);
      const now = JulianDate.fromDate(new Date())
      const start = JulianDate.addHours(now, -12, new JulianDate())
      const stop = JulianDate.addHours(now, 12, new JulianDate())

      cesiumViewer.clock.startTime = start.clone()
      cesiumViewer.clock.stopTime = stop.clone()
      cesiumViewer.clock.currentTime = now.clone()
      cesiumViewer.clock.clockRange = 2 // LOOP_STOP
      cesiumViewer.clock.multiplier = 500 // 1 hour per second
      cesiumViewer.clock.shouldAnimate = true

      // 🌎 Terrain & Lighting
      cesiumViewer.shadows = true
      cesiumViewer.scene.globe.enableLighting = true
      cesiumViewer.scene.globe.depthTestAgainstTerrain = true
      cesiumViewer.scene.globe.showGroundAtmosphere = true
      cesiumViewer.scene.globe.showWaterEffect = true
      cesiumViewer.scene.globe.baseColor = Color.BLACK

      // 🌫️ Fog
      cesiumViewer.scene.fog.enabled = true
      cesiumViewer.scene.fog.density = 0.0012
      cesiumViewer.scene.fog.minimumBrightness = 0.003

      // ☁️ Sky & Sunlight
      cesiumViewer.scene.skyAtmosphere = new SkyAtmosphere()
      cesiumViewer.scene.skyAtmosphere.hueShift = -0.8
      cesiumViewer.scene.skyAtmosphere.saturationShift = -0.7
      cesiumViewer.scene.skyAtmosphere.brightnessShift = -0.33
      if (cesiumViewer.scene.sun) {
        cesiumViewer.scene.sun.show = true
      }

       // 🔧 Calibration Offsets (Adjust these to align map)
        const LON_OFFSET = 0.03; // Positive = Shift Right (East)
        const LAT_OFFSET = -0.008; // Positive = Shift Up (North)

        const shiftPolygon = (entity: any) => {
            if (entity.polygon && cesiumViewer) { // Check viewer exists
                const hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer.clock.currentTime);
                if (hierarchy) {
                    const newPositions = hierarchy.positions.map((p: Cartesian3) => {
                        const carto = Cartographic.fromCartesian(p);
                        carto.longitude += CesiumMath.toRadians(LON_OFFSET);
                        carto.latitude += CesiumMath.toRadians(LAT_OFFSET);
                        // IMPORTANT: For shift to work with bars, we must base bars on the shifted positions
                        // Since we shift the entity polygon itself, calculating centroid from entity.polygon later should be fine!
                        return Cartesian3.fromRadians(carto.longitude, carto.latitude, carto.height);
                    });
                    entity.polygon.hierarchy = new ConstantProperty(new PolygonHierarchy(newPositions));
                }
            }
        };

        // 👆 Click Handler for Selection
        const handler = new ScreenSpaceEventHandler(cesiumViewer.scene.canvas);
        handler.setInputAction((movement: any) => {
            if (!cesiumViewer) return;
            const pickedObject = cesiumViewer.scene.pick(movement.position);
            
            if (defined(pickedObject) && pickedObject.id) {
                // If we pick a bar, we might want to get the underlying town?
                // Or just ignore bars? Bars are in customDataSource.
                
                const entity = pickedObject.id as Entity;
                // Check if it has a polygon (municipality)
                if (entity.polygon || entity.polyline) { 
                    // Retrieve Name
                    const name = entity.properties?.NOMBRE_MPI?.getValue() || 'Unknown Town';
                    
                    // Retrieve approximate location from picking position on globe
                    const cartesian = cesiumViewer.camera.pickEllipsoid(movement.position, cesiumViewer.scene.globe.ellipsoid);
                    if (cartesian) {
                        const cartographic = Cartographic.fromCartesian(cartesian);
                        const lat = CesiumMath.toDegrees(cartographic.latitude);
                        const lon = CesiumMath.toDegrees(cartographic.longitude);
                        
                        // Approximate altitude
                        const alt = 1250; 

                        selectedLocation.value = {
                            name,
                            lat, 
                            lon,
                            alt
                        }
                    }
                }
            } else {
                // Deselect? Or keep last selected?
                // selectedLocation.value = null; 
            }
        }, ScreenSpaceEventType.LEFT_CLICK);


        // 🗺️ Load Antioquia GeoJSON
        try {
            const dataSource = await GeoJsonDataSource.load('/antioquia.geojson', {
                fill: Color.TRANSPARENT,
                clampToGround: true, // ⛰️ Clamp fill to terrain
            })

            await cesiumViewer.dataSources.add(dataSource)
            municipalitiesDataSource = dataSource // 📍 Store reference

            // List of municipalities to highlight
            const rawTargetTowns = [
            'Jardín',
            'Andes',
            'Betania',
            'Ciudad Bolívar',
            'Támesis',
            'Urrao',
            'Hispania',
            'Fredonia',
            'La Pintada',
            'Amagá',
            'Santa Bárbara',
            'Venecia',
            'Abejorral',
            'El Retiro',
            'San Rafael',
            ]

            // Normalization helper: uppercase + remove accents
            const normalize = (str: string) => str.toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")

            // Valid GeoJSON names are usually simpler (e.g. "RETIRO" instead of "EL RETIRO")
            const aliasMap: Record<string, string> = {
                "EL RETIRO": "RETIRO"
            }

            const targetTowns = rawTargetTowns.map(t => {
                const upper = t.toUpperCase()
                return aliasMap[upper] || normalize(upper)
            })

            const entities = dataSource.entities.values
            for (let i = 0; i < entities.length; i++) {
                const entity = entities[i]
                if (!entity) continue

                const rawName = entity.properties?.NOMBRE_MPI?.getValue()
                
                let isTarget = false
                if (rawName && typeof rawName === 'string') {
                    // GeoJSON names might also need normalization to be safe
                    const name = normalize(rawName)
                    isTarget = targetTowns.includes(name)
                }

                if (isTarget) {
                    // Keep visible

                    // 🎨 Style Fill (Clamped)
                    if (entity.polygon) {
                    shiftPolygon(entity); // Apply shift before creating specific styles

                    entity.polygon.material = new ColorMaterialProperty(Color.CYAN.withAlpha(0.1))
                    entity.polygon.outline = new ConstantProperty(false) // Outlines don't work well on clamped polygons

                    // ✏️ Create Clamped Outline using Polyline
                    const hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer?.clock.currentTime) // Safe check
                    if (hierarchy) {
                        entity.polyline = new PolylineGraphics({
                        positions: hierarchy.positions,
                        width: 3,
                        material: Color.CYAN,
                        clampToGround: true,
                        })
                    }
                    }
                } else {
                    // Hide others
                    entity.show = false
                }
            }
            
            // 📊 Initial Bar Render
            setTimeout(() => {
            // 📊 Initial Widget Render
            setTimeout(() => {
                renderWeatherWidgets();
            }, 1000); // Small delay to ensure entities are ready/shifted
            }, 1000); // Small delay to ensure entities are ready/shifted

            // 🎥 Fly to Antioquia
            cesiumViewer.camera.flyTo({
            destination: Cartesian3.fromDegrees(-75.5, 6.5, 500000), // Approximate center of Antioquia
            duration: 3,
            })
        } catch (error) {
            console.error('Error loading GeoJSON:', error)
        }
        
        // ... (rest of geojson loading for depto) ...
        // 🗺️ Load Antioquia Department Outline
        try {
            const deptoDataSource = await GeoJsonDataSource.load('/antioquia_depto.geojson', {
            fill: Color.TRANSPARENT,
            clampToGround: true,
            })

            await cesiumViewer.dataSources.add(deptoDataSource)

            const deptoEntities = deptoDataSource.entities.values
            for (let i = 0; i < deptoEntities.length; i++) {
            const entity = deptoEntities[i]
            if (!entity) continue;
            
            if (entity.polygon) {
                shiftPolygon(entity); // Apply shift

                const hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer.clock.currentTime)
                
                // ✏️ Create Clamped Outline using Polyline
                if (hierarchy) {
                entity.polyline = new PolylineGraphics({
                    positions: hierarchy.positions,
                    width: 5,
                    material: Color.fromCssColorString('#00BD06'),
                    clampToGround: true,
                })
                }
                
                // ❌ Remove polygon fill to prevent blocking clicks on municipalities
                entity.polygon = undefined
            }
            }
        } catch (error) {
            console.error('Error loading Department GeoJSON:', error)
        }

    }
  }
})
</script>

<template>
  <div class="cesium-wrapper">
    <div id="cesiumContainer" ref="cesiumContainer"></div>
    <WeatherOverlay 
        :location="selectedLocation" 
        :weather-data="currentWeatherData"
        @switch-layer="handleLayerSwitch" 
        @weather-mode="handleWeatherMode" 
        @reset-camera="resetCamera"
    />
  </div>
</template>

<style scoped>
.cesium-wrapper {
  position: relative;
  width: 100%;
  height: 100vh;
}
#cesiumContainer {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

/* 🚫 Hide Default Cesium UI Elements */
:deep(.cesium-viewer-toolbar),
:deep(.cesium-viewer-animationContainer),
:deep(.cesium-viewer-timelineContainer),
:deep(.cesium-viewer-fullscreenContainer) {
  display: none !important;
}
</style>
