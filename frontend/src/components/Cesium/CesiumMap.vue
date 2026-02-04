<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const cesiumContainer = ref<HTMLElement | null>(null)
const selectedLocation = ref<{ name: string; lat: number; lon: number; alt: number } | null>(null)

// Viewer instance accessible to handleLayerSwitch
let viewer: Viewer | null = null

const handleLayerSwitch = (layerName: string) => {
    if (!viewer || !viewer.baseLayerPicker) return
    
    const models = viewer.baseLayerPicker.viewModel.imageryProviderViewModels
    // Helper to match partial names if needed, or exact
    let target = models.find((vm: any) => vm.name === layerName)
    
    // Fallback or fuzzy match for Bing
    if (!target && layerName.includes('Bing')) {
        target = models.find((vm: any) => vm.name.includes('Bing Maps Aerial'))
    }

    if (target) {
        viewer.baseLayerPicker.viewModel.selectedImagery = target
    } else {
        console.warn(`Layer ${layerName} not found in provider list.`)
    }
}

onMounted(async () => {
  if (cesiumContainer.value) {
    Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN

    // Assign to top-level variable
    viewer = new Viewer(cesiumContainer.value, {
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

    if (viewer.scene) {
        // 🌑 Initial Layer: Stadia
        if (viewer.baseLayerPicker) {
            const getProvider = (name: string) => 
               viewer?.baseLayerPicker.viewModel.imageryProviderViewModels.find((vm: any) => vm.name === name)

            const stadiaDark = getProvider('Stadia Alidade Smooth Dark')
            if (stadiaDark) {
               viewer.baseLayerPicker.viewModel.selectedImagery = stadiaDark
            }
        }

       // ⏳ Time-of-day simulation
      const now = JulianDate.fromDate(new Date())
      const start = JulianDate.addHours(now, -12, new JulianDate())
      const stop = JulianDate.addHours(now, 12, new JulianDate())

      viewer.clock.startTime = start.clone()
      viewer.clock.stopTime = stop.clone()
      viewer.clock.currentTime = now.clone()
      viewer.clock.clockRange = 2 // LOOP_STOP
      viewer.clock.multiplier = 3600 // 1 hour per second
      viewer.clock.shouldAnimate = true

      // 🌎 Terrain & Lighting
      viewer.shadows = true
      viewer.scene.globe.enableLighting = true
      viewer.scene.globe.depthTestAgainstTerrain = true
      viewer.scene.globe.showGroundAtmosphere = true
      viewer.scene.globe.showWaterEffect = true
      viewer.scene.globe.baseColor = Color.BLACK

      // 🌫️ Fog
      viewer.scene.fog.enabled = true
      viewer.scene.fog.density = 0.0012
      viewer.scene.fog.minimumBrightness = 0.003

      // ☁️ Sky & Sunlight
      viewer.scene.skyAtmosphere = new SkyAtmosphere()
      viewer.scene.skyAtmosphere.hueShift = -0.8
      viewer.scene.skyAtmosphere.saturationShift = -0.7
      viewer.scene.skyAtmosphere.brightnessShift = -0.33
      if (viewer.scene.sun) {
        viewer.scene.sun.show = true
      }

       // 🔧 Calibration Offsets (Adjust these to align map)
        const LON_OFFSET = 0.03; // Positive = Shift Right (East)
        const LAT_OFFSET = -0.008; // Positive = Shift Up (North)

        const shiftPolygon = (entity: any) => {
            if (entity.polygon && viewer) { // Check viewer exists
                const hierarchy = entity.polygon.hierarchy?.getValue(viewer.clock.currentTime);
                if (hierarchy) {
                    const newPositions = hierarchy.positions.map((p: Cartesian3) => {
                        const carto = Cartographic.fromCartesian(p);
                        carto.longitude += CesiumMath.toRadians(LON_OFFSET);
                        carto.latitude += CesiumMath.toRadians(LAT_OFFSET);
                        return Cartesian3.fromRadians(carto.longitude, carto.latitude, carto.height);
                    });
                    entity.polygon.hierarchy = new ConstantProperty(new PolygonHierarchy(newPositions));
                }
            }
        };

        // 👆 Click Handler for Selection
        const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((movement: any) => {
            if (!viewer) return;
            const pickedObject = viewer.scene.pick(movement.position);
            
            if (defined(pickedObject) && pickedObject.id) {
                const entity = pickedObject.id as Entity;
                // Check if it has a polygon (municipality)
                if (entity.polygon || entity.polyline) { 
                    // Retrieve Name
                    const name = entity.properties?.NOMBRE_MPI?.getValue() || 'Unknown Town';
                    
                    // Retrieve approximate location from picking position on globe
                    const cartesian = viewer.camera.pickEllipsoid(movement.position, viewer.scene.globe.ellipsoid);
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

            await viewer.dataSources.add(dataSource)

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
                    const hierarchy = entity.polygon.hierarchy?.getValue(viewer?.clock.currentTime) // Safe check
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

            // 🎥 Fly to Antioquia
            viewer.camera.flyTo({
            destination: Cartesian3.fromDegrees(-75.5, 6.5, 500000), // Approximate center of Antioquia
            duration: 3,
            })
        } catch (error) {
            console.error('Error loading GeoJSON:', error)
        }

        // 🗺️ Load Antioquia Department Outline
        try {
            const deptoDataSource = await GeoJsonDataSource.load('/antioquia_depto.geojson', {
            fill: Color.TRANSPARENT,
            clampToGround: true,
            })

            await viewer.dataSources.add(deptoDataSource)

            const deptoEntities = deptoDataSource.entities.values
            for (let i = 0; i < deptoEntities.length; i++) {
            const entity = deptoEntities[i]
            if (!entity) continue;
            
            if (entity.polygon) {
                shiftPolygon(entity); // Apply shift

                const hierarchy = entity.polygon.hierarchy?.getValue(viewer.clock.currentTime)
                
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
    <WeatherOverlay :location="selectedLocation" @switch-layer="handleLayerSwitch" />
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
