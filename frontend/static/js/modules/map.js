// frontend/static/js/modules/map.js

import * as PIXI from 'pixi.js';
import { DisplayObjectPool } from './pixi/DisplayObjectPool.js';
import { TokenFactory } from './pixi/TokenFactory.js';

export class GameMap {
    constructor(canvasId) {
        this.app = new PIXI.Application();
        this.ready = this._init(canvasId);
    }

    async _init(canvasId) {
        await this.app.init({
            canvas: document.getElementById(canvasId),
            resizeTo: window,
            backgroundColor: 0x1a1a1a
        });

        this.gridContainer = new PIXI.Container();
        this.tokensContainer = new PIXI.Container();
        this.app.stage.addChild(this.gridContainer);
        this.app.stage.addChild(this.tokensContainer);

        // Пул создаёт токены через renderer — он доступен только после init()
        this.tokenPool = new DisplayObjectPool(() => TokenFactory.createDefaultToken(this.app.renderer));
        console.log('[MAP] Object pool initialized.');
    }

    async drawHexGrid(size, cols, rows) {
        await this.ready;

        const graphics = new PIXI.Graphics();
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
        graphics.stroke({ width: 1, color: 0x333333, alpha: 0.2 });
        this.gridContainer.addChild(graphics);
    }

    async createPlayerToken(playerId, x, y) {
        await this.ready;
        let token = this.tokenPool.acquire();
        token.visible = true;
        token.position.set(x, y);
        token.playerId = playerId;
        this.tokensContainer.addChild(token);
        return token;
    }

    removePlayerToken(token) {
        if (!token) return;
        this.tokensContainer.removeChild(token);
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