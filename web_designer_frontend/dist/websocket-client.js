/**
 * WebSocket Client for ESP32OS Collaborative Editor
 * Manages WebSocket connection, reconnection, and message routing
 */

export class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.reconnectTimer = null;
        this.handlers = new Map();
        this.connected = false;
        this.userId = null;
        this.username = null;
        this.projectId = null;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('[WS] Connected to', this.url);
                this.connected = true;
                clearTimeout(this.reconnectTimer);
                this.emit('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('[WS] Received:', message);
                    this.handleMessage(message);
                } catch (err) {
                    console.error('[WS] Failed to parse message:', err);
                }
            };

            this.ws.onerror = (error) => {
                console.error('[WS] Error:', error);
                this.emit('error', error);
            };

            this.ws.onclose = () => {
                console.log('[WS] Disconnected');
                this.connected = false;
                this.emit('disconnected');
                this.scheduleReconnect();
            };
        } catch (err) {
            console.error('[WS] Connection failed:', err);
            this.scheduleReconnect();
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectTimer) return;
        console.log(`[WS] Reconnecting in ${this.reconnectInterval}ms...`);
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, this.reconnectInterval);
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * Send message to server
     */
    send(message) {
        if (!this.connected || !this.ws) {
            console.warn('[WS] Not connected, cannot send:', message);
            return false;
        }
        try {
            const json = JSON.stringify(message);
            this.ws.send(json);
            console.log('[WS] Sent:', message);
            return true;
        } catch (err) {
            console.error('[WS] Send failed:', err);
            return false;
        }
    }

    /**
     * Handle incoming message
     */
    handleMessage(message) {
        const { type, op } = message;
        const eventType = type || op;
        if (!eventType) {
            console.warn('[WS] Message missing "type" or "op" field:', message);
            return;
        }

        // Emit to registered handlers
        this.emit(eventType, message);
        this.emit('message', message);
    }

    /**
     * Register event handler
     */
    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event).push(handler);
    }

    /**
     * Unregister event handler
     */
    off(event, handler) {
        if (!this.handlers.has(event)) return;
        const handlers = this.handlers.get(event);
        const index = handlers.indexOf(handler);
        if (index >= 0) {
            handlers.splice(index, 1);
        }
    }

    /**
     * Emit event to handlers
     */
    emit(event, data) {
        if (!this.handlers.has(event)) return;
        const handlers = this.handlers.get(event);
        for (const handler of handlers) {
            try {
                handler(data);
            } catch (err) {
                console.error(`[WS] Handler error for ${event}:`, err);
            }
        }
    }

    // Protocol methods

    /**
     * Join project session
     */
    join(projectId, username) {
        this.projectId = projectId;
        this.username = username;
        // Backend expects 'user_name' and infers project from WS path
        return this.send({
            type: 'join',
            user_name: username
        });
    }

    /**
     * Send cursor position
     */
    sendCursor(x, y) {
        return this.send({
            type: 'cursor',
            x: x,
            y: y
        });
    }

    /**
     * Add widget
     */
    addWidget(widget) {
        return this.send({
            type: 'widget_add',
            widget: widget
        });
    }

    /**
     * Update widget
     */
    updateWidget(widgetId, updates) {
        return this.send({
            type: 'widget_update',
            widget_id: widgetId,
            changes: updates
        });
    }

    /**
     * Delete widget
     */
    deleteWidget(widgetId) {
        return this.send({
            type: 'widget_delete',
            widget_id: widgetId
        });
    }

    /**
     * Undo last operation
     */
    undo() {
        return this.send({
            type: 'undo'
        });
    }

    /**
     * Redo last undone operation
     */
    redo() {
        return this.send({
            type: 'redo'
        });
    }
}
