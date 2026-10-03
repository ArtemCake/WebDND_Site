// frontend/static/js/modules/pixi/TokenFactory.js

import * as PIXI from 'pixi.js';

const COLORS = {
    blue: 0x3498db,
    red: 0xe74c3c,
    green: 0x2ecc71,
    yellow: 0xf1c40f,
    purple: 0x9b59b6,
    gray: 0x95a5a6
};

export class TokenFactory {
    /**
     * @param {PIXI.Renderer} renderer - рендерер приложения (нужен для генерации текстуры в v8)
     */
    static createColoredCircle(renderer, colorKey = 'blue', radius = 32) {
        const color = COLORS[colorKey] || COLORS.blue;

        const graphics = new PIXI.Graphics();
        graphics.circle(radius, radius, radius).fill(color);

        const texture = renderer.generateTexture(graphics);
        return new PIXI.Sprite(texture);
    }

    static createDefaultToken(renderer) {
        return this.createColoredCircle(renderer, 'gray');
    }
}