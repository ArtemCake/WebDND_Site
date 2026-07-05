// rename-script.js

const fs = require('fs-extra');
const path = require('path');

// --- НАСТРОЙКА ПУТЕЙ ---
// Путь к папке с JS-файлами
const jsDistPath = path.resolve(__dirname, 'dist/js');
// Путь к папке с CSS-файлами
const cssDistPath = path.resolve(__dirname, 'dist/css');

// --- ФУНКЦИЯ ДЛЯ ПЕРЕИМЕНОВАНИЯ ФАЙЛОВ ---
function renameFile(folderPath, prefix, newName) {
  // Читаем содержимое указанной папки
  fs.readdir(folderPath, (err, files) => {
    // Если папка не найдена или пуста, просто выходим
    if (err) {
      // console.log(`Папка ${folderPath} не найдена. Пропускаем.`);
      return;
    }

    // Ищем файл, который начинается с указанного префикса (например, 'main-' или 'style-')
    const targetFile = files.find(file => file.startsWith(prefix));

    if (targetFile) {
      const oldPath = path.join(folderPath, targetFile);
      const newPath = path.join(folderPath, newName);

      // Переименовываем файл
      fs.rename(oldPath, newPath, (renameErr) => {
        if (renameErr) {
          console.error(`❌ Ошибка при переименовании ${prefix} файла:`, renameErr);
          return;
        }
        console.log(`✅ Файл '${targetFile}' успешно переименован в '${newName}'`);
      });
    } else {
      // console.log(`Файл с префиксом '${prefix}' в папке ${folderPath} не найден.`);
    }
  });
}

// --- ВЫПОЛНЕНИЕ СКРИПТА ---

// 1. Переименовываем JS-файл в папке dist/js
renameFile(jsDistPath, 'main-', 'main.min.js');

// 2. Переименовываем CSS-файл в папке dist/css
renameFile(cssDistPath, 'app-', 'style.min.css'); // Обратите внимание на расширение .css