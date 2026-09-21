// vite.config.js

import { defineConfig } from 'vite';
import path from 'path';
import { exec } from 'child_process';


export default defineConfig({
  root: '.',

  // Vite будет отдавать файлы из frontend/ напрямую:
  // /static/fonts/Cinzel-Bold.woff2 → frontend/static/fonts/Cinzel-Bold.woff2
  publicDir: path.resolve(__dirname, 'frontend'),

  server: {
    port: 8080,
    open: true
  },

  css: {
    modules: {
      generateScopedName: '[name]__[local]___[hash:base64:5]'
    },
    preprocessorOptions: {
      scss: {
        additionalData: `
          @use "@/static/css/modules/base/_variables" as *;
        `
      }
    }
  },

  build: {
    outDir: 'dist',
    assetsDir: 'static',
    emptyOutDir: true,

    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'frontend/static/js/main.js'),
        app: path.resolve(__dirname, 'frontend/static/css/style.scss')
      },

      output: {
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',

        assetFileNames: (assetInfo) => {
          if (!assetInfo.name) return 'assets/[name]-[hash].[ext]';

          const extType = assetInfo.name.split('.')[1]?.toLowerCase();

          if (extType === 'css') return 'css/[name]-[hash].[ext]';
          else if (/png|jpe?g|svg|gif|tiff|bmp|webp|ico/i.test(extType)) {
            return 'frontend/static/images/[name][extname]';
          }
          else if (/woff2|woff/i.test(extType)) {
            return 'frontend/static/fonts/[name][extname]';
          }
          else if (/md/i.test(extType)) {
            return 'frontend/static/docs/[name][extname]';
          }
          else {
            return 'frontend/static/assets/[name]-[hash][extname]';
          }
        }
      }
    },

    onCloseBundle: async () => {
      console.log('[VITE] Сборка завершена. Выполняю нормализацию имен файлов...');
      return new Promise((resolve, reject) => {
        const scriptPath = path.resolve(__dirname, 'rename-script.js');
        const child = exec(
          `node "${scriptPath}"`,
          { stdio: 'inherit' },
          (error) => {
            if (error) {
              console.error('\n❌ [BUILD FAILED] Скрипт rename-script.js вернул ошибку:');
              console.error(error.message);
              reject(error);
              return;
            }
            console.log('\n✅ [SUCCESS] Post-build обработка (rename-script.js) завершена.');
            resolve();
          }
        );
      });
    }
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'frontend'),
      '~': path.resolve(__dirname, 'frontend', 'static')
    }
  },

  esbuild: {
    jsxFactory: 'h',
    jsxFragment: 'Fragment'
  }
});