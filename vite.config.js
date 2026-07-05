// vite.config.js

import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "./static/css/modules/_variables.scss";`
      }
    },
    modules: {
      generateScopedName: '[name]__[local]___[hash:base64:5]'
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'static',
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'static/js/main.js'),
        app: path.resolve(__dirname, 'static/css/style.css')
      },
      output: {
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          // Защита от undefined
          if (!assetInfo.name) {
            return 'assets/[name]-[hash].[ext]';
          }

          const extType = assetInfo.name.split('.')[1]?.toLowerCase();

          if (extType === 'css') {
            return 'css/[name]-[hash].[ext]';
          } else if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return 'static/assets/images/[name]-[hash][extname]';
          } else {
            return 'static/assets/[name]-[hash][extname]';
          }
        }
      }
    }
  }
});
