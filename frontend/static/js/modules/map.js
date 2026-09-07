// frontend/static/js/modules/map.js

import * as PIXI from 'pixi.js';
import { BLEND_MODES } from '@pixi/constants';

export class GameMap {
    constructor(containerId) {
        this.app = new PIXI.Application({
            backgroundColor: 0x0a0f14,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true
        });

        document.getElementById(containerId).appendChild(this.app.view);

        // Слой тумана войны (самый верхний)
        this.fogContainer = new PIXI.Container();
        this.app.stage.addChild(this.fogContainer);
        this.applyGlobalFog();
    }

    applyGlobalFog() {
        const fullFog = new PIXI.Graphics();
        fullFog.beginFill(0x000000);
        fullFog.drawRect(0, 0, this.app.screen.width, this.app.screen.height);
        fullFog.endFill();
        this.fogContainer.addChild(fullFog);
    }

    revealCircle(x, y, radius) {
        const maskGraphics = new PIXI.Graphics();
        maskGraphics.beginFill(0xffffff);
        maskGraphics.drawCircle(x, y, radius);
        maskGraphics.endFill();

        const maskSprite = new PIXI.Sprite(maskGraphics.generateCanvasTexture());
        maskSprite.x = 0;
        maskSprite.y = 0;

        // Используем правильную константу из импорта выше
        maskSprite.blendMode = BLEND_MODES.DESTINATION_OUT;

        this.fogContainer.addChild(maskSprite);
    }

    drawHexGrid(size, cols, rows) { // Переименовано для ясности: columns & rows
        for (let q = 0; q < cols; q++) {
            for (let r = 0; r < rows; r++) { // <--- ИСПРАВЛЕНО: сравнение с rows
                const gfx = new PIXI.Graphics();

                // Расчет координат гекса (смещение "вперехлест")
                const offsetX = size * 1.5 * q;
                const offsetY = size * Math.sqrt(3) * (r + (q % 2) * 0.5);

                this.drawHex(gfx, offsetX, offsetY, size, 0x2d2d3c);
                this.app.stage.addChild(gfx);
            }
        }
    }

    drawHex(graphics, cx, cy, size, color) {
        graphics.lineStyle(1, 0x333333, 0.5);
        graphics.beginFill(color);

        // Рисуем правильный шестиугольник
        for (let i = 0; i < 6; i++) { // Здесь 'i' объявлен правильно!
            const angle = (Math.PI / 3) * i - (Math.PI / 6); // Смещение угла, чтобы гекс стоял "плоско" сверху
            const px = cx + size * Math.cos(angle);
            const py = cy + size * Math.sin(angle);

            if (i === 0) {
                graphics.moveTo(px, py);
            } else {
                graphics.lineTo(px, py);
            }
        }
        graphics.endFill();
    }
}