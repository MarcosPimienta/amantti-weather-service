<template>
  <div id="cesiumContainer" ref="cesiumContainer"></div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  Viewer,
  createWorldTerrainAsync,
  Ion,
  Color,
  SkyAtmosphere,
  Cartesian3,
  JulianDate,
  GeoJsonDataSource,
  HeightReference,
  PolylineGraphics,
  ColorMaterialProperty,
  ConstantProperty,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const cesiumContainer = ref<HTMLElement | null>(null)

onMounted(async () => {
  if (cesiumContainer.value) {
    Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN

    const viewer = new Viewer(cesiumContainer.value, {
      terrainProvider: await createWorldTerrainAsync({}),
      timeline: true,
      animation: true,
    })

    if (viewer.scene) {
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
              entity.polygon.material = new ColorMaterialProperty(Color.CYAN.withAlpha(0.1))
              entity.polygon.outline = new ConstantProperty(false) // Outlines don't work well on clamped polygons

              // ✏️ Create Clamped Outline using Polyline
              const hierarchy = entity.polygon.hierarchy?.getValue(viewer.clock.currentTime)
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

<style scoped>
#cesiumContainer {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>
