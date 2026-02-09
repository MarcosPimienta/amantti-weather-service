<template>
  <div class="cloud-debug-panel glass-card">
    <h3>☁️ Cumulus Cloud Debugger</h3>
    
    <div class="control-group">
      <label>Maximum Size X (Width): {{ settings.maxSizeX }}m</label>
      <input type="range" v-model.number="settings.maxSizeX" min="1000" max="100000" step="500" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Maximum Size Y (Length): {{ settings.maxSizeY }}m</label>
      <input type="range" v-model.number="settings.maxSizeY" min="1000" max="100000" step="500" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Maximum Size Z (Height): {{ settings.maxSizeZ }}m</label>
      <input type="range" v-model.number="settings.maxSizeZ" min="100" max="20000" step="100" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Texture Scale (Zoom): {{ settings.textureScale }}x</label>
      <!-- Controls the 'scale' property. Higher = zoomed in texture? Or repeated? -->
      <input type="range" v-model.number="settings.textureScale" min="1" max="100" step="1" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Slice: {{ settings.slice }}</label>
      <input type="range" v-model.number="settings.slice" min="0" max="1" step="0.05" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Brightness: {{ settings.brightness }}</label>
      <input type="range" v-model.number="settings.brightness" min="0" max="1" step="0.05" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Altitude (Base Z): {{ settings.altitude }}m</label>
      <input type="range" v-model.number="settings.altitude" min="1000" max="10000" step="100" @input="emitUpdate">
    </div>

    <div class="control-group">
      <label>Number of Clouds: {{ settings.count }}</label>
      <input type="range" v-model.number="settings.count" min="1" max="200" step="1" @input="emitUpdate">
    </div>
    
    <button @click="$emit('refresh')" class="refresh-btn">🔄 Respawn Clouds</button>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue';

const props = defineProps<{
  initialSettings: any
}>();

const emit = defineEmits(['update', 'refresh']);

const settings = reactive({ ...props.initialSettings });

const emitUpdate = () => {
  emit('update', settings);
};

// Sync if props change externally
watch(() => props.initialSettings, (newVal) => {
  Object.assign(settings, newVal);
}, { deep: true });

</script>

<style scoped>
.cloud-debug-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 320px;
  background: rgba(0, 0, 0, 0.8);
  padding: 15px;
  border-radius: 10px;
  color: white;
  z-index: 100;
  max-height: 90vh;
  overflow-y: auto;
  pointer-events: auto;
  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
  font-family: sans-serif;
}

h3 {
  margin-top: 0;
  color: #a5f3fc;
  border-bottom: 1px solid rgba(255,255,255,0.2);
  padding-bottom: 10px;
  font-size: 1.1rem;
}

.control-group {
  margin-bottom: 15px;
}

label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 5px;
  color: #ddd;
}

input[type="range"] {
  width: 100%;
  cursor: pointer;
}

.refresh-btn {
  width: 100%;
  padding: 10px;
  background: #0ea5e9;
  border: none;
  border-radius: 5px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  margin-top: 10px;
  transition: background 0.2s;
}

.refresh-btn:hover {
  background: #0284c7;
}

/* Scrollbar styling */
.cloud-debug-panel::-webkit-scrollbar {
  width: 8px;
}
.cloud-debug-panel::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}
.cloud-debug-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}
</style>
