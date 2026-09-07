// vite.config.js

import { defineConfig } from 'vite';
import path from 'path';
import { exec } from 'child_process';
// ВАЖНО: Если используете React или Vue, добавьте соответствующие плагины здесь:
// import react from '@vitejs/plugin-react';
// import vue from '@vitejs/plugin-vue';

export default defineConfig({
  // --- КОРЕНЬ ПРОЕКТА ---
  // Указываем корень относительно расположения этого файла
  root: '.',

  server: {
    port: 8080,
    open: true
  },

  css: {
    modules: {
      // Локальная область видимости CSS классов
      generateScopedName: '[name]__[local]___[hash:base64:5]'
    },

    preprocessorOptions: {
      scss: {
        // ЭТО КРИТИЧЕСКИ ВАЖНАЯ СТРОКА ДЛЯ ТЗ:
        // Внедряем переменные во ВСЕ .scss файлы проекта автоматически.
        // Это решает проблему "Unknown variable" в модулях.
        additionalData: `
          @use "@/static/css/modules/_variables" as *;
        `
      }
    }
  },

  build: {
    outDir: 'dist',           // Куда складывать готовую сборку
    assetsDir: 'static',       // Папка внутри dist для картинок/шрифтов
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
          else if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return 'static/assets/images/[name]-[hash][extname]';
          } else {
            return 'static/assets/[name]-[hash][extname]';
          }
        }
      }
    },

    // --- БЛОК POST-BUILD (VITE HOOKS) ---
    onCloseBundle: async () => {
      console.log('[VITE] Сборка завершена. Выполняю нормализацию имен файлов...');

      return new Promise((resolve, reject) => {
        // Используем __dirname для гарантии нахождения файла rename-script.js
        const scriptPath = path.resolve(__dirname, 'rename-script.js');

        const child = exec(
          `node "${scriptPath}"`,
          { stdio: 'inherit' }, // Чтобы логи из node-скрипта падали прямо в консоль Vite
          (error) => {
            if (error) {
              console.error('\n❌ [BUILD FAILED] Скрипт rename-script.js вернул ошибку:');
              console.error(error.message);

              // Раскомментируйте строку ниже, если хотите, чтобы
              // ошибка нейминга НЕ ломала всю сборку продакшена:
              // resolve();
              // return;

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
      // Алиас для удобства импорта JS модулей (@/components/...)
      '@': path.resolve(__dirname, 'frontend')
    }
  },

  // Опционально: настройки линтера ESLint внутри Vite
  esbuild: {
    jsxFactory: 'h',
    jsxFragment: 'Fragment'
  }
});