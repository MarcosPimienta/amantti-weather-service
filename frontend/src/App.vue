<script setup lang="ts">
import CesiumMap from '@/components/Cesium/CesiumMap.vue';

</script>

<template>
  <main class="app">
    <CesiumMap />
  </main>
</template>

<style scoped>
.app {
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>
