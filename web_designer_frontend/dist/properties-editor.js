/**
 * Properties Editor for ESP32OS Collaborative Editor
 * Dynamic properties panel for selected widgets
 */

export class PropertiesEditor {
    constructor(wsClient, renderer) {
        this.ws = wsClient;
        this.renderer = renderer;
        this.propertiesPanel = document.getElementById('properties-content');
        this.currentWidget = null;
        this.updating = false; // Prevent echo updates
    }

    /**
     * Show properties for selected widget
     */
    showWidget(widgetId, widget) {
        this.currentWidget = { id: widgetId, ...widget };
        this.render();
    }

    /**
     * Clear properties (no selection)
     */
    clear() {
        this.currentWidget = null;
        this.propertiesPanel.innerHTML = `
            <div class="no-selection">
                <div>No widget selected</div>
                <div class="hint">Click a widget to edit its properties</div>
            </div>
        `;
    }

    /**
     * Render properties form
     */
    render() {
        if (!this.currentWidget) {
            this.clear();
            return;
        }

        const { id, type, x, y, width, height, text, color } = this.currentWidget;

        const html = `
            <div class="widget-properties">
                <h4>Widget Properties</h4>
                
                <div class="form-group">
                    <label>Type</label>
                    <input type="text" id="prop-type" value="${type}" readonly disabled>
                </div>

                <div class="form-group">
                    <label>ID</label>
                    <input type="text" id="prop-id" value="${id}" readonly disabled>
                </div>

                <div class="form-group">
                    <label>X Position</label>
                    <input type="number" id="prop-x" value="${x}" min="0">
                </div>

                <div class="form-group">
                    <label>Y Position</label>
                    <input type="number" id="prop-y" value="${y}" min="0">
                </div>

                <div class="form-group">
                    <label>Width</label>
                    <input type="number" id="prop-width" value="${width}" min="1">
                </div>

                <div class="form-group">
                    <label>Height</label>
                    <input type="number" id="prop-height" value="${height}" min="1">
                </div>

                ${text !== undefined ? `
                <div class="form-group">
                    <label>Text</label>
                    <input type="text" id="prop-text" value="${text || ''}">
                </div>
                ` : ''}

                ${color !== undefined ? `
                <div class="form-group">
                    <label>Color</label>
                    <input type="color" id="prop-color" value="${color || '#252526'}">
                </div>
                ` : ''}

                <button class="btn btn-primary btn-block" id="delete-widget-btn">
                    Delete Widget
                </button>
            </div>
        `;

        this.propertiesPanel.innerHTML = html;
        this.attachEventListeners();
    }

    /**
     * Attach event listeners to form inputs
     */
    attachEventListeners() {
        const inputs = {
            x: document.getElementById('prop-x'),
            y: document.getElementById('prop-y'),
            width: document.getElementById('prop-width'),
            height: document.getElementById('prop-height'),
            text: document.getElementById('prop-text'),
            color: document.getElementById('prop-color')
        };

        // Remove null inputs
        Object.keys(inputs).forEach(key => {
            if (!inputs[key]) delete inputs[key];
        });

        // Add change listeners
        Object.entries(inputs).forEach(([prop, input]) => {
            input.addEventListener('change', () => {
                this.updateProperty(prop, this.parseValue(prop, input.value));
            });

            // For number inputs, also update on input (real-time)
            if (input.type === 'number') {
                input.addEventListener('input', () => {
                    this.updateProperty(prop, this.parseValue(prop, input.value));
                });
            }
        });

        // Delete button
        const deleteBtn = document.getElementById('delete-widget-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.deleteWidget();
            });
        }
    }

    /**
     * Parse input value to correct type
     */
    parseValue(prop, value) {
        if (['x', 'y', 'width', 'height'].includes(prop)) {
            return parseInt(value, 10);
        }
        return value;
    }

    /**
     * Update widget property
     */
    updateProperty(prop, value) {
        if (!this.currentWidget || this.updating) return;

        // Update local state
        this.currentWidget[prop] = value;

        // Update renderer immediately for local feedback
        this.renderer.updateWidget(this.currentWidget.id, { [prop]: value });

        // Send update to server
        this.ws.updateWidget(this.currentWidget.id, { [prop]: value });
    }

    /**
     * Delete current widget
     */
    deleteWidget() {
        if (!this.currentWidget) return;

        if (confirm(`Delete widget ${this.currentWidget.id}?`)) {
            this.ws.deleteWidget(this.currentWidget.id);
            this.renderer.deleteWidget(this.currentWidget.id);
            this.clear();
        }
    }

    /**
     * Handle external widget update (from WebSocket)
     */
    onWidgetUpdated(widgetId, updates) {
        // If this is the currently selected widget, update form
        if (this.currentWidget && this.currentWidget.id === widgetId) {
            this.updating = true;
            Object.assign(this.currentWidget, updates);
            
            // Update form inputs
            Object.entries(updates).forEach(([prop, value]) => {
                const input = document.getElementById(`prop-${prop}`);
                if (input) {
                    input.value = value;
                }
            });
            
            this.updating = false;
        }
    }

    /**
     * Handle widget deletion (from WebSocket)
     */
    onWidgetDeleted(widgetId) {
        if (this.currentWidget && this.currentWidget.id === widgetId) {
            this.clear();
        }
    }
}
