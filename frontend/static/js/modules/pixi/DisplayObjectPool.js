// frontend/static/js/modules/pixi/DisplayObjectPool.js

/**
 * Универсальный пул объектов для снижения нагрузки на GC.
 * Хранит неиспользуемые инстансы и выдает их по запросу.
 */
export class DisplayObjectPool {
    constructor(createFn) {
        this._pool = [];
        this._createFn = createFn;
    }

    /**
     * Получает объект из пула или создает новый.
     * @returns {PIXI.DisplayObject}
     */
    acquire() {
        return this._pool.length > 0 ? this._pool.pop() : this._createFn();
    }

    /**
     * Возвращает объект в пул для дальнейшего переиспользования.
     * Сбрасывает базовые свойства видимости.
     * @param {PIXI.DisplayObject} obj
     */
    release(obj) {
        // Базовая очистка перед возвратом в пул
        obj.visible = false;
        obj.position.set(0, 0);

        if (obj.clear && typeof obj.clear === 'function') {
            obj.clear();
        }

        this._pool.push(obj);
    }

    /**
     * Полная очистка пула (например, при смене сцены/сессии).
     */
    clear() {
        this._pool.length = 0;
    }

    get size() {
        return this._pool.length;
    }
}