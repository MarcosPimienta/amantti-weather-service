<template>
  <div id="cesiumContainer" ref="cesiumContainer">
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  Viewer,
  createWorldTerrainAsync,
  Ion,
  Color,
  SkyAtmosphere,
  Cartesian3,
  JulianDate
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

const cesiumContainer = ref<HTMLElement | null>(null);

onMounted(async ()=>{
  if (cesiumContainer.value) {
    Ion.defaultAccessToken = 'YOUR_CESIUM_ION_ACCESS_TOKEN';
    const viewer = new Viewer(cesiumContainer.value, {
      terrainProvider: await createWorldTerrainAsync({})
    });
    if (viewer.scene) {
      // ⏳ Time-of-day simulation
      const now = JulianDate.fromDate(new Date());
      const start = JulianDate.addHours(now, -12, new JulianDate());
      const stop = JulianDate.addHours(now, 12, new JulianDate());

      viewer.clock.startTime = start.clone();
      viewer.clock.stopTime = stop.clone();
      viewer.clock.currentTime = now.clone();
      viewer.clock.clockRange = 2; // LOOP_STOP
      viewer.clock.multiplier = 3600; // 1 hour per second
      viewer.clock.shouldAnimate = true;

      // 🌎 Terrain & Lighting
      viewer.shadows = true;
      viewer.scene.globe.enableLighting = true;
      viewer.scene.globe.depthTestAgainstTerrain = true;
      viewer.scene.globe.showGroundAtmosphere = true;
      viewer.scene.globe.showWaterEffect = true;
      viewer.scene.globe.baseColor = Color.BLACK;

      // 🌫️ Fog
      viewer.scene.fog.enabled = true;
      viewer.scene.fog.density = 0.0012;
      viewer.scene.fog.minimumBrightness = 0.003;

      // ☁️ Sky & Sunlight
      viewer.scene.skyAtmosphere = new SkyAtmosphere();
      viewer.scene.skyAtmosphere.hueShift = -0.8;
      viewer.scene.skyAtmosphere.saturationShift = -0.7;
      viewer.scene.skyAtmosphere.brightnessShift = -0.33;
      if (viewer.scene.sun) {
        viewer.scene.sun.show = true;
      }

      // 🎥 Initial camera position
      viewer.camera.setView({
        destination: Cartesian3.fromDegrees(-74.0060, 40.7128, 15000000)
      });
    }
  }
});
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
