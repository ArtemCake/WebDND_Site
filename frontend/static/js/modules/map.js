// frontend/static/js/modules/map.js

import * as PIXI from 'pixi.js';
import { DisplayObjectPool } from './pixi/DisplayObjectPool.js';
import { TokenFactory } from './pixi/TokenFactory.js';

export class GameMap {
    constructor(canvasId) {
        this.app = new PIXI.Application({
            view: document.getElementById(canvasId),
            resizeTo: window,
            backgroundColor: 0x1a1a1a
        });

        this.gridContainer = new PIXI.Container();
        this.tokensContainer = new PIXI.Container();

        this.app.stage.addChild(this.gridContainer);
        this.app.stage.addChild(this.tokensContainer);

        // --- ИНИЦИАЛИЗАЦИЯ ПУЛА ---
        // Передаем фабричную функцию, которая знает, как создать чистый токен
        this.tokenPool = new DisplayObjectPool(() => TokenFactory.createDefaultToken());
        console.log('[MAP] Object pool initialized.');
    }

    drawHexGrid(size, cols, rows) {
        const graphics = new PIXI.Graphics();
        graphics.lineStyle(1, 0x333333, 0.2);

        for (let c = 0; c < cols; c++) {
            for (let r = 0; r < rows; r++) {
                const x = c * size * 1.5;
                const y = r * size * Math.sqrt(3) + (c % 2 * size * Math.sqrt(3) / 2);

                graphics.moveTo(x + size, y);
                for (let i = 1; i <= 6; i++) {
                    const angle = (Math.PI / 3) * i;
                    graphics.lineTo(x + size + size * Math.cos(angle), y + size * Math.sin(angle));
                }
            }
        }

        this.gridContainer.addChild(graphics);
    }

    /**
     * Создание токена игрока через объектный пул.
     * @param {string} playerId - Уникальный ID игрока.
     * @param {number} x - Координата X.
     * @param {number} y - Координата Y.
     */
    createPlayerToken(playerId, x, y) {
        // Вместо new PIXI.Graphics() берем готовый объект из пула
        let token = this.tokenPool.acquire();

        // Если нужно изменить цвет под конкретного игрока (расширяемо)
        // token.tint = ...

        token.visible = true;
        token.position.set(x, y);

        // Привязываем ID для возможности возврата в пул
        token.playerId = playerId;

        this.tokensContainer.addChild(token);
        return token;
    }

    /**
     * Удаляет токен со сцены, возвращая его в пул.
     * Это предотвращает утечки памяти и снижает лаги.
     * @param {PIXI.DisplayObject} token
     */
    removePlayerToken(token) {
        if (!token) return;

        // Убираем из контейнера отображения
        this.tokensContainer.removeChild(token);

        // Возвращаем в пул для переиспользования
        this.tokenPool.release(token);

        console.log(`[MAP] Token returned to pool. Pool size: ${this.tokenPool.size}`);
    }

    updateTokenPosition(token, x, y) {
        if (token && token.visible) {
            token.x = x;
            token.y = y;
        }
    }
}