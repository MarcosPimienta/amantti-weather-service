import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import path from 'node:path'
import cesium from 'vite-plugin-cesium'

const cesiumSource = 'node_modules/cesium/Source'
const cesiumWorkers = '../Build/Cesium/Workers'

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    viteStaticCopy({
      targets: [
        { src: path.join(cesiumSource, cesiumWorkers), dest: 'Cesium' },
        { src: path.join(cesiumSource, 'Assets'), dest: 'Cesium' },
        { src: path.join(cesiumSource, 'Widgets'), dest: 'Cesium' },
        { src: path.join(cesiumSource, 'ThirdParty'), dest: 'Cesium' },
      ]
    }),
    cesium(),
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/Cesium'),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    target: 'esnext',
    assetsInlineLimit: 0,
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
