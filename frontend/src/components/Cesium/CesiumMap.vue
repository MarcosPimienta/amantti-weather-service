<template>
  <div id="cesiumContainer">
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {Viewer, createWorldTerrainAsync, Ion, Color} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

const cesiumContainer = ref<HTMLElement | null>(null);

onMounted(async ()=>{
  if (cesiumContainer.value) {
    Ion.defaultAccessToken = 'YOUR_CESIUM_ION_ACCESS_TOKEN';
    const viewer = new Viewer(cesiumContainer.value, {
      terrainProvider: await createWorldTerrainAsync({})
    });
    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.depthTestAgainstTerrain = true;
    viewer.scene.globe.showGroundAtmosphere = true;
    viewer.scene.globe.showWaterEffect = true;
    viewer.scene.globe.baseColor = Color.BLACK;
    viewer.scene.fog.enabled = true;
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
