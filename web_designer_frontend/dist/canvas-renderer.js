/**
 * Canvas Renderer for ESP32OS Collaborative Editor
 * Handles rendering widgets, grid, selection, zoom/pan
 */

export class CanvasRenderer {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.width = 800;
        this.height = 600;
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.showGrid = true;
        this.gridSize = 20;
        this.widgets = new Map(); // widgetId -> widget data
        this.selectedWidget = null;
        this.selectedWidgets = new Set();

        // Performance optimization: offscreen grid cache
        this.gridCanvas = document.createElement('canvas');
        this.gridCtx = this.gridCanvas.getContext('2d');
        this.gridDirty = true;
        
        // Render throttling
        this.renderPending = false;
        this.lastRenderTime = 0;

        this.setupCanvas();
    }

    setupCanvas() {
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        this.gridCanvas.width = this.width;
        this.gridCanvas.height = this.height;
        this.gridDirty = true;
    }

    /**
     * Clear canvas
     */
    clear() {
        this.ctx.clearRect(0, 0, this.width, this.height);
    }

    /**
     * Render everything (throttled)
     */
    render() {
        if (this.renderPending) return;
        this.renderPending = true;
        requestAnimationFrame(() => {
            this._renderImmediate();
            this.renderPending = false;
            this.lastRenderTime = performance.now();
        });
    }

    /**
     * Immediate render (internal)
     */
    _renderImmediate() {
        this.clear();
        
        this.ctx.save();
        this.ctx.translate(this.panX, this.panY);
        this.ctx.scale(this.zoom, this.zoom);

        if (this.showGrid) {
            this._renderCachedGrid();
        }

        this.renderWidgets();

        if (this.selectedWidgets.size > 0) {
            for (const id of this.selectedWidgets) {
                this.renderSelection(id);
            }
            if (this.selectedWidgets.size > 1) {
                this.renderGroupSelection();
            }
        } else if (this.selectedWidget) {
            this.renderSelection(this.selectedWidget);
        }

        this.ctx.restore();
    }

    /**
     * Render grid using offscreen cache
     */
    _renderCachedGrid() {
        if (this.gridDirty) {
            this._regenerateGridCache();
            this.gridDirty = false;
        }
        this.ctx.drawImage(this.gridCanvas, 0, 0);
    }

    /**
     * Regenerate grid cache
     */
    _regenerateGridCache() {
        const ctx = this.gridCtx;
        ctx.clearRect(0, 0, this.width, this.height);
        
        const gridSize = this.gridSize || 20;
        const gridColor = '#30363d';

        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x <= this.width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.height);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y <= this.height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.width, y);
            ctx.stroke();
        }
    }

    /**
     * Render grid (legacy - kept for reference)
     */
    renderGrid() {
        const gridSize = this.gridSize || 20;
        const gridColor = '#30363d';

        this.ctx.strokeStyle = gridColor;
        this.ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x <= this.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y <= this.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }

    /**
     * Render all widgets
     */
    renderWidgets() {
        for (const [, widget] of this.widgets) {
            this.renderWidget(widget);
        }
    }

    /**
     * Render single widget
     */
    renderWidget(widget) {
        const { type, x, y, width, height, text, color } = widget;

        this.ctx.save();

        // Background
        this.ctx.fillStyle = color || '#252526';
        this.ctx.fillRect(x, y, width, height);

        // Border
        this.ctx.strokeStyle = '#444d56';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x, y, width, height);

        // Text
        if (text) {
            this.ctx.fillStyle = '#cccccc';
            this.ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(text, x + width / 2, y + height / 2);
        }

        // Type indicator
        this.ctx.fillStyle = '#6e6e6e';
        this.ctx.font = '10px monospace';
        this.ctx.textAlign = 'left';
        this.ctx.fillText(type, x + 4, y + 12);

        this.ctx.restore();
    }

    /**
     * Render selection handles
     */
    renderSelection(widgetId) {
        const widget = this.widgets.get(widgetId);
        if (!widget) return;

        const { x, y, width, height } = widget;
        const handleSize = 6;

        this.ctx.save();

        // Selection border
        this.ctx.strokeStyle = '#007acc';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x - 1, y - 1, width + 2, height + 2);

        // Corner handles
        this.ctx.fillStyle = '#007acc';
        const handles = [
            [x, y], // top-left
            [x + width, y], // top-right
            [x, y + height], // bottom-left
            [x + width, y + height] // bottom-right
        ];

        for (const [hx, hy] of handles) {
            this.ctx.fillRect(
                hx - handleSize / 2,
                hy - handleSize / 2,
                handleSize,
                handleSize
            );
        }

        this.ctx.restore();
    }

    /**
     * Render group selection bounding box
     */
    renderGroupSelection() {
        if (this.selectedWidgets.size < 2) return;
        const rect = this.getBoundingBox(Array.from(this.selectedWidgets));
        if (!rect) return;
        const handleSize = 8;

        this.ctx.save();
        this.ctx.setLineDash([6, 4]);
        this.ctx.strokeStyle = '#007acc';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(rect.x - 1, rect.y - 1, rect.width + 2, rect.height + 2);
        this.ctx.setLineDash([]);

        this.ctx.fillStyle = '#007acc';
        const handles = [
            [rect.x, rect.y],
            [rect.x + rect.width, rect.y],
            [rect.x, rect.y + rect.height],
            [rect.x + rect.width, rect.y + rect.height]
        ];
        for (const [hx, hy] of handles) {
            this.ctx.fillRect(
                hx - handleSize / 2,
                hy - handleSize / 2,
                handleSize,
                handleSize
            );
        }
        this.ctx.restore();
    }

    /**
     * Set zoom level
     */
    setZoom(zoom) {
        this.zoom = Math.max(0.1, Math.min(5.0, zoom));
        this.render();
    }

    /**
     * Zoom in
     */
    zoomIn() {
        this.setZoom(this.zoom + 0.1);
    }

    /**
     * Zoom out
     */
    zoomOut() {
        this.setZoom(this.zoom - 0.1);
    }

    /**
     * Reset zoom
     */
    resetZoom() {
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.render();
    }

    /**
     * Pan canvas
     */
    pan(dx, dy) {
        this.panX += dx;
        this.panY += dy;
        this.render();
    }

    /**
     * Toggle grid
     */
    toggleGrid() {
        this.showGrid = !this.showGrid;
        this.gridDirty = true;
        this.render();
        return this.showGrid;
    }

    /**
     * Add widget
     */
    addWidget(id, widget) {
        this.widgets.set(id, widget);
        this.render();
    }

    /**
     * Update widget
     */
    updateWidget(id, updates) {
        const widget = this.widgets.get(id);
        if (!widget) return;
        Object.assign(widget, updates);
        this.render();
    }

    /**
     * Delete widget
     */
    deleteWidget(id) {
        this.widgets.delete(id);
        if (this.selectedWidget === id) {
            this.selectedWidget = null;
        }
        if (this.selectedWidgets.has(id)) {
            this.selectedWidgets.delete(id);
        }
        this.render();
    }

    /**
     * Select widget
     */
    selectWidget(id) {
        this.selectedWidget = id;
        this.selectedWidgets.clear();
        this.selectedWidgets.add(id);
        this.render();
        return this.widgets.get(id);
    }

    /**
     * Clear selection
     */
    clearSelection() {
        this.selectedWidget = null;
        this.selectedWidgets.clear();
        this.render();
    }

    /**
     * Toggle selection for a widget (multi-select)
     */
    toggleSelection(id) {
        if (this.selectedWidgets.has(id)) {
            this.selectedWidgets.delete(id);
        } else {
            this.selectedWidgets.add(id);
        }
        this.selectedWidget = this.selectedWidgets.size === 1 ? [...this.selectedWidgets][0] : null;
        this.render();
    }

    /**
     * Set selection to specific ids
     */
    setSelection(ids) {
        this.selectedWidgets = new Set(ids);
        this.selectedWidget = this.selectedWidgets.size === 1 ? [...this.selectedWidgets][0] : null;
        this.render();
    }

    /**
     * Get widget at position
     */
    getWidgetAt(x, y) {
        // Transform mouse coords to canvas coords
        const cx = (x - this.panX) / this.zoom;
        const cy = (y - this.panY) / this.zoom;

        // Check widgets in reverse order (top to bottom)
        const widgets = Array.from(this.widgets.entries()).reverse();
        for (const [id, widget] of widgets) {
            if (cx >= widget.x && cx <= widget.x + widget.width &&
                cy >= widget.y && cy <= widget.y + widget.height) {
                return id;
            }
        }
        return null;
    }

    /**
     * Transform screen coords to canvas coords
     */
    screenToCanvas(screenX, screenY) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (screenX - rect.left - this.panX) / this.zoom;
        const y = (screenY - rect.top - this.panY) / this.zoom;
        return { x, y };
    }

    /**
     * Clear all widgets
     */
    clearWidgets() {
        this.widgets.clear();
        this.selectedWidget = null;
        this.render();
    }

    /**
     * Get current state info
     */
    getInfo() {
        return {
            zoom: this.zoom.toFixed(2),
            widgets: this.widgets.size,
            selected: this.selectedWidget ? 1 : 0,
            grid: this.showGrid
        };
    }

    /**
     * Set grid size
     */
    setGridSize(size) {
        const s = parseInt(size, 10);
        if (!isNaN(s) && s > 0 && s < 200) {
            this.gridSize = s;
            this.gridDirty = true;
            this.render();
        }
    }

    /**
     * Move widget to front (topmost)
     */
    moveToFront(id) {
        const w = this.widgets.get(id);
        if (!w) return;
        this.widgets.delete(id);
        this.widgets.set(id, w);
        this.render();
    }

    /**
     * Move widget to back (bottom)
     */
    moveToBack(id) {
        const entries = Array.from(this.widgets.entries());
        if (!this.widgets.has(id)) return;
        const w = this.widgets.get(id);
        this.widgets = new Map([[id, w]]);
        for (const [k, v] of entries) {
            if (k !== id) this.widgets.set(k, v);
        }
        this.render();
    }

    /**
     * Get bounding box of all or provided widget ids
     */
    getBoundingBox(ids = null) {
        const items = ids ? ids.map(id => [id, this.widgets.get(id)]) : Array.from(this.widgets.entries());
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let count = 0;
        for (const [, w] of items) {
            if (!w) continue;
            count++;
            minX = Math.min(minX, w.x);
            minY = Math.min(minY, w.y);
            maxX = Math.max(maxX, w.x + w.width);
            maxY = Math.max(maxY, w.y + w.height);
        }
        if (count === 0) return null;
        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    }

    /**
     * Zoom and pan to fit rectangle with margin
     */
    zoomToRect(rect, margin = 20) {
        if (!rect) return;
        const viewport = {
            x: rect.x - margin,
            y: rect.y - margin,
            width: rect.width + 2 * margin,
            height: rect.height + 2 * margin
        };
        const scaleX = this.width / viewport.width;
        const scaleY = this.height / viewport.height;
        const scale = Math.max(0.1, Math.min(5.0, Math.min(scaleX, scaleY)));
        this.zoom = scale;
        this.panX = -scale * viewport.x + (this.width - scale * viewport.width) / 2;
        this.panY = -scale * viewport.y + (this.height - scale * viewport.height) / 2;
        this.render();
    }
}
