<template>
  <div class="weather-overlay">
    <!-- Single Sidebar Container -->
    <div class="sidebar">
      
      <!-- Controls Row: Icons + Layer Picker -->
      <div class="controls-row">
        <div class="atmosphere-icons">
          <div 
            class="icon-circle" 
            :class="{ active: activeWeatherMode === 'clear' }"
            title="Clear Sky"
            @click="setWeatherMode('clear')"
          >
            ☀️
          </div>
          <div 
            class="icon-circle" 
            :class="{ active: activeWeatherMode === 'rain' }"
            title="Rain probability"
            @click="setWeatherMode('rain')"
          >
            💧
          </div>
          <div 
            class="icon-circle" 
            :class="{ active: activeWeatherMode === 'humidity' }"
            title="Humidity"
            @click="setWeatherMode('humidity')"
          >
            🌫️
          </div>
        </div>
        
        <!-- Layer Picker -->
        <div class="layer-control">
          <div class="icon-circle layer-btn" @click="showLayers = !showLayers" title="Map Layers">
            🗺️
          </div>
          
          <div class="layer-dropdown glass-card" v-if="showLayers">
            <div 
              class="layer-option" 
              :class="{ active: currentLayer === 'Stadia Alidade Smooth Dark' }"
              @click="selectLayer('Stadia Alidade Smooth Dark')"
            >
              🌑 Stadia Dark
            </div>
            <div 
              class="layer-option" 
              :class="{ active: currentLayer === 'Bing Maps Aerial' }"
              @click="selectLayer('Bing Maps Aerial')"
            >
              🛰️ Bing Satellite
            </div>
          </div>
        </div>
      </div>

      <!-- Aggregated Summaries -->
      <div class="glass-card summary-card">
        <h3>Region Summary</h3>
        <div class="stat-row">
          <span class="label">Avg Temp</span>
          <span class="value">{{ summary.avgTemp }}°C</span>
        </div>
        <div class="stat-row">
          <span class="label">Avg Humidity</span>
          <span class="value">{{ summary.avgHumidity }}%</span>
        </div>
        <div class="stat-row">
          <span class="label">Active Alerts</span>
          <span class="value alert-count">{{ summary.alerts }}</span>
        </div>
      </div>

      <!-- Location & Time Control (Fixed at Bottom) -->
      <div class="glass-card">
        <h2 class="town-name">{{ location?.name || '--' }}</h2>
        <div class="coordinates">
          <span>LAT: {{ location?.lat.toFixed(4) || '--' }}</span> | <span>LON: {{ location?.lon.toFixed(4) || '--' }}</span>
        </div>
        <div class="altitude">
          ALT: {{ location?.alt.toFixed(0) || '--' }}m
        </div>

        <div class="divider"></div>

        <div class="time-controls">
          <label>
            <span>Start Time</span>
            <input type="datetime-local" v-model="timeRange.start" />
          </label>
          <label>
            <span>End Time</span>
            <input type="datetime-local" v-model="timeRange.end" />
          </label>
        </div>

        <div class="current-timestamp">
          {{ formattedCurrentTime }}
        </div>
      </div>
    
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface LocationData {
  name: string
  lat: number
  lon: number
  alt: number
}

interface SummaryData {
  avgTemp: number
  avgHumidity: number
  alerts: number
}

const props = defineProps<{
  location: LocationData | null
  summary?: SummaryData
}>()

const emit = defineEmits<{
  (e: 'switch-layer', layerName: string): void
  (e: 'weather-mode', mode: string): void
}>()

// Default summary if not provided
const summary = computed(() => props.summary || {
  avgTemp: 24.5,
  avgHumidity: 78,
  alerts: 2
})

const timeRange = ref({
  start: new Date().toISOString().slice(0, 16),
  end: new Date().toISOString().slice(0, 16)
})

const currentTime = ref(new Date())
setInterval(() => {
  currentTime.value = new Date()
}, 1000)

const formattedCurrentTime = computed(() => {
  return currentTime.value.toLocaleString(undefined, {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
})

// Weather Mode Logic
const activeWeatherMode = ref('clear') // Default

const setWeatherMode = (mode: string) => {
  activeWeatherMode.value = mode
  emit('weather-mode', mode)
}

// Layer Logic
const showLayers = ref(false)
const currentLayer = ref('Stadia Alidade Smooth Dark')

const selectLayer = (layer: string) => {
  currentLayer.value = layer
  emit('switch-layer', layer)
  showLayers.value = false
}
</script>

<style scoped>
.weather-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Let clicks pass through */
  z-index: 10;
  padding: 2rem;
  box-sizing: border-box;
}

/* Sidebar Column Layout */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 320px; /* Fixed width for the column */
  pointer-events: auto; /* Enable clicks */
}

/* Glassmorphism Card Style */
.glass-card {
  background: rgba(20, 20, 30, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  color: #fff;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  width: 100%;
  transition: all 0.3s ease;
}

.glass-card:hover {
  background: rgba(30, 30, 45, 0.75);
  border-color: rgba(255, 255, 255, 0.2);
}

/* Typography */
h2.town-name {
  margin: 0 0 0.5rem 0;
  font-size: 1.8rem;
  font-weight: 700;
  background: linear-gradient(135deg, #fff 0%, #a5f3fc 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 2px 10px rgba(165, 243, 252, 0.2);
}

h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  color: #fbbf24;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.coordinates, .altitude {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 0.25rem;
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 1rem 0;
}

/* Inputs */
.time-controls label {
  display: flex;
  flex-direction: column;
  margin-bottom: 0.75rem;
  font-size: 0.8rem;
  color: #ccc;
}

.time-controls input {
  margin-top: 0.25rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 8px;
  color: #fff;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}

.time-controls input:focus {
  border-color: #a5f3fc;
}

/* Timestamp */
.current-timestamp {
  font-family: monospace;
  font-size: 0.9rem;
  color: #a5f3fc;
  text-align: right;
  margin-top: 0.5rem;
}

/* Stats */
.stat-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.stat-row .value {
  font-weight: 700;
  color: #fff;
}

.stat-row .alert-count {
  color: #ef4444;
  text-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
}

/* Controls Row */
.controls-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  /* Make sidebar contents align nicely */
  width: 100%; 
}

.atmosphere-icons {
  display: flex;
  gap: 1rem;
  flex-grow: 1; /* Push layer control to end if needed, or keep tight */
}

.icon-circle {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  cursor: pointer;
  transition: transform 0.2s, background 0.2s;
}

.icon-circle:hover {
  transform: scale(1.1);
  background: rgba(255, 255, 255, 0.2);
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.3);
}

.icon-circle.active {
  background: rgba(165, 243, 252, 0.3);
  border-color: #a5f3fc;
  box-shadow: 0 0 15px rgba(165, 243, 252, 0.5);
  transform: scale(1.1);
}

/* Layer Control */
.layer-control {
  position: relative;
  margin-left: auto; /* Push to right of the row */
}

.layer-btn {
  border-color: #a5f3fc;
  color: #a5f3fc;
}

.layer-dropdown {
  position: absolute;
  top: 0;
  left: 110%; /* Show to the right of the button now */
  width: 200px;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 20;
}

.layer-option {
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 0.9rem;
}

.layer-option:hover {
  background: rgba(255, 255, 255, 0.1);
}

.layer-option.active {
  background: rgba(165, 243, 252, 0.2);
  color: #a5f3fc;
  border: 1px solid rgba(165, 243, 252, 0.3);
}
</style>
