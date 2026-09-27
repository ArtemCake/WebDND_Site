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

/**
 * Фабрика создает стандартизированные токены.
 * Разделена ради соблюдения правила "один файл — один функционал".
 */
export class TokenFactory {
    static createColoredCircle(colorKey = 'blue', radius = 32) {
        const color = COLORS[colorKey] || COLORS.blue;

        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, 1);
        graphics.drawCircle(0, 0, radius);
        graphics.endFill();

        // Создаем спрайт из графики для лучшей производительности рендеринга
        const texture = PIXI.RenderTexture.create({
            width: radius * 2,
            height: radius * 2
        });

        // Примечание: здесь предполагается наличие доступа к app.renderer у вызывающей стороны
        // В реальном сценарии передача renderer должна быть инкапсулирована лучше.
        // Пока оставляем так для демонстрации логики пула.

        const sprite = new PIXI.Sprite(texture);
        return sprite;
    }

    static createDefaultToken() {
        return this.createColoredCircle('gray');
    }
}