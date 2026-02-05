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
  Cartesian4
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const cesiumContainer = ref<HTMLElement | null>(null)
const selectedLocation = ref<{ name: string; lat: number; lon: number; alt: number } | null>(null)
const currentWeatherMode = ref<string[]>(['clear']) // Default mode
const currentWeatherData = ref<{ temp: number; rain: number; humidity: number } | null>(null)
// Store local polygon positions for the emitter
const currentPolygonCenter = ref<Cartesian3 | null>(null);

// Viewer instance accessible 
let cesiumViewer: Viewer | null = null

// Rain System
let rainSystem: ParticleSystem | null = null


// Data Source for 3D Bars
let barDataSource: CustomDataSource | null = null
let municipalitiesDataSource: GeoJsonDataSource | null = null // 📍 Added reliable reference

// Mock Data Cache to keep values consistent
const townDataCache: Record<string, { temp: number, rain: number, humidity: number }> = {}

const getTownData = (townName: string) => {
    if (!townDataCache[townName]) {
        townDataCache[townName] = {
            temp: 15 + Math.random() * 20, // 15-35 C
            rain: Math.random() < 0.3 ? 0 : Math.random() * 50, // 0-50 mm
            humidity: 40 + Math.random() * 60 // 40-100 %
        }
    }
    return townDataCache[townName]
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



// 🌧️ Camera-Attached Rain System
let rainUpdateListener: (() => void) | null = null;
const currentRainRadius = ref(1500.0);

const refreshRainEffect = () => {
    if (!cesiumViewer) return;
    
    // Cleanup existing
    if (rainSystem) {
        cesiumViewer.scene.primitives.remove(rainSystem);
        rainSystem = null;
    }
    if (rainUpdateListener) {
        cesiumViewer.scene.preUpdate.removeEventListener(rainUpdateListener);
        rainUpdateListener = null;
    }

    const location = selectedLocation.value;
    const data = currentWeatherData.value;
    
    // Conditions to show rain:
    // 1. Location selected
    // 2. Data available 
    if (!location || !data) {
        return;
    }

    // Rain Logic
    if (data.rain > 0 && currentWeatherMode.value.includes('rain')) {
         
        // 💧 Intensity Scaling
        // Rain is 0-50 mm
        const intensityNode = Math.min(data.rain / 50, 1.0); 
        const emissionRate = 200 * intensityNode * 15.0; 
        
        // Speed
        const speed = 15.0 + (intensityNode * 10.0);

        // 🎥 Camera-Attached Rain System
        const rainImageSize = new Cartesian2(4, 15);
        
        rainSystem = new ParticleSystem({
            image: createRainCanvas(),
            startColor: Color.WHITE.withAlpha(0.6),
            endColor: Color.WHITE.withAlpha(0.0),
            startScale: 1.0,
            endScale: 1.0,
            minimumParticleLife: 1.5, 
            maximumParticleLife: 1.5,
            minimumSpeed: speed * 0.9,
            maximumSpeed: speed * 1.1,
            imageSize: rainImageSize,
            emissionRate: emissionRate,
            // Box Emitter around camera
            emitter: new BoxEmitter(new Cartesian3(1000.0, 1000.0, 800.0)),
            lifetime: 16.0,
            modelMatrix: Matrix4.IDENTITY, 
            updateCallback: (particle: any, dt: number) => {
               // Gravity (Down relative to world)
               particle.velocity.z = -speed; 
               particle.velocity.x = 0;
               particle.velocity.y = 0;
            }
        });
        
        cesiumViewer.scene.primitives.add(rainSystem);

        // 👂 Update Loop: Keep Rain System centered on Camera
        rainUpdateListener = () => {
             if (!cesiumViewer || !rainSystem) return;
             
             const cameraPos = cesiumViewer.camera.position;
             // Calculate matrix at camera position with ENU orientation
             // This keeps "Up" aligned with World Up
             const params = Transforms.eastNorthUpToFixedFrame(cameraPos);
             
             rainSystem.modelMatrix = params;
        };
        
        cesiumViewer.scene.preUpdate.addEventListener(rainUpdateListener);
    }
}

const createTempBarGradient = (temp: number, maxTemp: number = 50) => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    const ratio = Math.min(Math.max(temp / maxTemp, 0), 1);
    
    // Gradient from 0 to Ratio of the full scale
    // Full Scale: 0.0 (Blue) -> 0.5 (Yellow) -> 1.0 (Red)
    
    const grad = ctx.createLinearGradient(0, 256, 0, 0); // Bottom to Top
    
    // Always start at Blue
    grad.addColorStop(0, 'blue');
    
    if (ratio <= 0.5) {
        // Range is [0, ratio] which is sub-segment of [0, 0.5] (Blue->Yellow)
        // End color is interp(Blue, Yellow, ratio / 0.5)
        const endColor = interpolateColor('blue', 'yellow', ratio / 0.5);
        grad.addColorStop(1, endColor);
    } else {
        // Range crosses Yellow (0.5)
        // Yellow happens at 0.5 / ratio in local space
        const yellowPos = 0.5 / ratio;
        grad.addColorStop(yellowPos, 'yellow');
        
        // End color is interp(Yellow, Red, (ratio - 0.5) / 0.5)
        const endColor = interpolateColor('yellow', 'red', (ratio - 0.5) / 0.5);
        grad.addColorStop(1, endColor);
    }

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 256);
    return canvas;
}

const renderDataBars = async () => {
    if (!cesiumViewer || !barDataSource) return;
    
    // Debug log
    console.log(`[BarDebug] Render called. Modes: ${currentWeatherMode.value.join(', ')}`);

    barDataSource.entities.removeAll();

    // 🔒 Filter: Only show if a location is selected
    if (!selectedLocation.value) {
        console.log("[BarDebug] No location selected. Clearing bars.");
        return;
    }

    const activeModes = currentWeatherMode.value;
    if (activeModes.length === 0) return;

    // Scalar configs with Offsets (in degrees, approx)
    // 0.015 degrees is roughly ~1.5km at equator, good enough for separation
    type ModeConfig = { scale: number; color: Color; material?: MaterialProperty; prop: 'temp' | 'rain' | 'humidity'; label: string; offsetLon: number; offsetLat: number };
    
    const config: Record<string, ModeConfig> = {
        'clear': { 
            scale: 200, 
            color: Color.ORANGE, 
            // Material will be generated dynamically
            prop: 'temp', 
            label: 'Temp', 
            offsetLon: 0, 
            offsetLat: 0 
        }, 
        'rain': { scale: 500, color: Color.DEEPSKYBLUE, prop: 'rain', label: 'Rain', offsetLon: 0.015, offsetLat: 0 },
        'humidity': { scale: 100, color: Color.WHITESMOKE.withAlpha(0.8), prop: 'humidity', label: 'Hum', offsetLon: -0.015, offsetLat: 0 }
    }
    
    // Use specific data source
    if (!municipalitiesDataSource) {
        console.warn("[BarDebug] No municipalities data source found yet.");
        return;
    }

    const entities = municipalitiesDataSource.entities.values;
    
    let barsAdded = 0;

    for (let i = 0; i < entities.length; i++) {
        const entity = entities[i];
        if (!entity?.polygon) continue; 
        
        const rawName = entity.properties?.NOMBRE_MPI?.getValue();
        if (!rawName) continue;

        // 🎯 Exact Match Filter: Only show for selected town
        if (rawName !== selectedLocation.value.name) continue;

        const data = getTownData(rawName);

        // Iterate over all active modes
        for (const mode of activeModes) {
             const cfg = config[mode];
             if (!cfg) continue;

             const value = data[cfg.prop];

             if (value <= 0) continue; 

             // Calculate Centroid
             const hierarchy = entity.polygon.hierarchy?.getValue(cesiumViewer.clock.currentTime);
             if (hierarchy) {
                 const positions = hierarchy.positions;
                 const boundingSphere = BoundingSphere.fromPoints(positions);
                 const center = boundingSphere.center;
                 
                 const carto = Cartographic.fromCartesian(center);
                 const shiftedLon = carto.longitude + CesiumMath.toRadians(cfg.offsetLon * (180/Math.PI)); // Convert offset deg to rad? No, offset is in degrees, so convert scale.
                 // Wait, carto.longitude is in Radians. 
                 // My offsetLon is in Degrees.
                 // So: newLonRad = oldLonRad + toRadians(offsetDeg)
                 
                 const finalLon = carto.longitude + CesiumMath.toRadians(cfg.offsetLon);
                 const finalLat = carto.latitude + CesiumMath.toRadians(cfg.offsetLat);

                 // Height calculation
                 const barHeight = value * cfg.scale * 2;
                 
                 console.log(`[BarDebug] Adding bar for ${rawName} [${mode}]: Val=${value.toFixed(1)}`);
                 
                 let material: MaterialProperty | Color = cfg.color;
                 if (mode === 'clear') {
                     // 🌡️ Dynamic Heat Gradient
                     material = new ImageMaterialProperty({
                         image: createTempBarGradient(value, 50), // Max 50C
                         transparent: true
                     });
                 } else if (cfg.material) {
                     material = cfg.material;
                 }

                 // Create Bar Entity
                 barDataSource.entities.add({
                     position: Cartesian3.fromRadians(
                         finalLon,
                         finalLat,
                         0
                     ),
                     box: {
                         dimensions: new Cartesian3(1500, 1500, barHeight), // Slightly thinner bars to fit side-by-side
                         material: material,
                         outline: false,
                         heightReference: HeightReference.CLAMP_TO_GROUND
                     }
                 });
                 barsAdded++;
             }
        }
    }
    console.log(`[BarDebug] Total bars added: ${barsAdded}`);
}

const handleWeatherMode = (modes: string[]) => {
    currentWeatherMode.value = modes;
    refreshRainEffect();
    renderDataBars();
}

// 👀 Watch for Selection Changes to update bars
// � Watch for Selection Changes to update bars
watch(selectedLocation, (newLoc) => {
    if (newLoc) {
        const data = getTownData(newLoc.name);
        currentWeatherData.value = data;
    } else {
        currentWeatherData.value = null;
    }
    refreshRainEffect();
    renderDataBars();
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

    // Assign to top-level variable
    cesiumViewer = new Viewer(cesiumContainer.value, {
      terrainProvider: await createWorldTerrainAsync({}),
      timeline: false,
      animation: false, // ❌ Disable Animation Dial
      infoBox: false,
      selectionIndicator: false,
      // ❌ Disable Default Widgets (Top Right)
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      baseLayerPicker: true, // ✅ Keep enabled for logic, hide via CSS
    })

    if (cesiumViewer.scene) {
        // ... (existing scene setup) ... 
        
        // 📊 Add Custom Data Source for Bars
        barDataSource = new CustomDataSource('bars');
        
        cesiumViewer.dataSources.add(barDataSource);

        // ... (existing logic) ...
        
        // ... Inside GeoJSON load ...
        // After loading GeoJSON and filtering, call renderDataBars() once to init
        
        // 🌑 Initial Layer: Stadia
        if (cesiumViewer.baseLayerPicker) {
            const getProvider = (name: string) => 
               cesiumViewer?.baseLayerPicker.viewModel.imageryProviderViewModels.find((vm: any) => vm.name === name)

            const stadiaDark = getProvider('Stadia Alidade Smooth Dark')
            if (stadiaDark) {
               cesiumViewer.baseLayerPicker.viewModel.selectedImagery = stadiaDark
            }
        }

       // ⏳ Time-of-day simulation
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
                renderDataBars();
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
