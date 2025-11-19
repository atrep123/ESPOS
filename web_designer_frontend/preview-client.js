/**
 * ESP32 Simulator Live Preview Client
 * Connects to WebSocket bridge for real-time preview
 */

export class PreviewClient {
    constructor(bridgeUrl = 'ws://localhost:8765') {
        this.bridgeUrl = bridgeUrl;
        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2 seconds
        this.onStatusChange = null; // Callback for connection status
        this.onSimEvent = null; // Callback for simulator events
        this.simState = { scene: null, bg: null, buttons: { A: false, B: false, C: false } };
    }

    /**
     * Connect to the bridge server
     */
    async connect() {
        try {
            this.ws = new WebSocket(this.bridgeUrl);

            this.ws.onopen = () => {
                console.log('Connected to simulator bridge');
                this.connected = true;
                this.reconnectAttempts = 0;
                
                // Register as designer client
                this.send({
                    op: 'register',
                    type: 'designer'
                });

                if (this.onStatusChange) {
                    this.onStatusChange('connected');
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (err) {
                    console.error('Error parsing message:', err);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                if (this.onStatusChange) {
                    this.onStatusChange('error');
                }
            };

            this.ws.onclose = () => {
                console.log('Disconnected from simulator bridge');
                this.connected = false;
                
                if (this.onStatusChange) {
                    this.onStatusChange('disconnected');
                }

                // Attempt reconnection
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connect(), this.reconnectDelay);
                } else {
                    console.log('Max reconnect attempts reached');
                    if (this.onStatusChange) {
                        this.onStatusChange('failed');
                    }
                }
            };

        } catch (err) {
            console.error('Connection error:', err);
            if (this.onStatusChange) {
                this.onStatusChange('error');
            }
        }
    }

    /**
     * Disconnect from bridge
     */
    disconnect() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }
    }

    /**
     * Handle incoming messages from bridge
     */
    handleMessage(data) {
        const op = data.op;

        switch (op) {
            case 'registered':
                console.log('Registered with bridge as:', data.type);
                break;

            case 'design_state':
                console.log('Received current design state from bridge');
                // Could sync local state if needed
                break;

            case 'design_synced':
                console.log('Design synchronized with other clients');
                break;

            case 'sim_event':
                this.handleSimEvent(data.event_type, data.data);
                break;

            default:
                console.warn('Unknown message type:', op);
        }
    }

    /**
     * Handle simulator events and update internal state
     */
    handleSimEvent(type, payload) {
        if (type === 'button' && payload && payload.button) {
            this.simState.buttons[payload.button] = !!payload.pressed;
        } else if (type === 'bg' && payload) {
            this.simState.bg = payload.bg;
        } else if (type === 'scene' && payload) {
            this.simState.scene = payload.scene;
        }
        if (this.onSimEvent) {
            this.onSimEvent(type, payload, { ...this.simState });
        }
    }

    /**
     * Send message to bridge
     */
    send(data) {
        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('Cannot send - not connected to bridge');
        }
    }

    /**
     * Send complete design update to simulator
     */
    sendDesign(design) {
        if (!this.connected) {
            console.warn('Cannot send design - not connected');
            return false;
        }

        this.send({
            op: 'design_update',
            design: design
        });

        return true;
    }

    /**
     * Send widget add operation
     */
    addWidget(widget) {
        if (!this.connected) return false;

        this.send({
            op: 'widget_add',
            widget: widget
        });

        return true;
    }

    /**
     * Send widget update operation
     */
    updateWidget(widgetId, changes) {
        if (!this.connected) return false;

        this.send({
            op: 'widget_update',
            widget_id: widgetId,
            changes: changes
        });

        return true;
    }

    /**
     * Send widget delete operation
     */
    deleteWidget(widgetId) {
        if (!this.connected) return false;

        this.send({
            op: 'widget_delete',
            widget_id: widgetId
        });

        return true;
    }

    /**
     * Get connection status
     */
    isConnected() {
        return this.connected;
    }
}
