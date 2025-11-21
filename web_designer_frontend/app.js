/**
 * ESP32OS Collaborative UI Designer - Main Application
 * Integrates all modules and handles UI interactions
 */

import { CanvasRenderer } from './canvas-renderer.js';
import { PreviewClient } from './preview-client.js';
import { PropertiesEditor } from './properties-editor.js';
import { UndoRedoUI } from './undo-redo-ui.js';
import { WebSocketClient } from './websocket-client.js';

class App {
    ws = null;
    previewClient = null;
    previewConnected = false;
    renderer = null;
    undoRedoUI = null;
    propertiesEditor = null;
    cursors = new Map(); // userId -> cursor element
    draggedWidget = null;
    dragOffsetX = 0;
    dragOffsetY = 0;
    dragState = null; // Tracks current drag operation state (move/resize metadata)
    wsMoveThrottle = null;
    panState = null; // { startX, startY, startPanX, startPanY }
    spacePressed = false;
    clipboard = null; // Copied widget data
    autoSaveInterval = null;

    /**
     * Toggle simulator preview connection
     */
    togglePreview() {
        const previewBtn = document.getElementById('previewBtn');
        
        if (!this.previewClient) {
            // Initialize preview client (bridge listens on 8765)
            this.previewClient = new PreviewClient('ws://localhost:8765');
            
            // Setup status change callback
            this.previewClient.onStatusChange = (status) => {
                this.onPreviewStatusChange(status);
            };
            // Simulator event callback
            this.previewClient.onSimEvent = (_type, _payload, simState) => {
                this.updateSimulatorStatus(simState);
            };
        }
        
        if (this.previewConnected) {
            // Disconnect
            this.previewClient.disconnect();
            this.previewConnected = false;
            previewBtn.textContent = '▶ Preview';
            previewBtn.classList.remove('active');
            this.updateStatus(null, 'Preview disconnected');
        } else {
            // Connect
            this.previewClient.connect();
            previewBtn.textContent = '⏸ Connecting...';
            this.updateStatus(null, 'Connecting to preview...');
        }
    }

    /**
     * Handle preview connection status changes
     */
    onPreviewStatusChange(status) {
        const previewBtn = document.getElementById('previewBtn');
        const simStatus = document.getElementById('sim-status');
        
        switch (status) {
            case 'connected':
                this.previewConnected = true;
                previewBtn.textContent = '⏸ Disconnect Preview';
                previewBtn.classList.add('active');
                this.updateStatus(null, 'Preview connected - live sync active');
                if (simStatus) simStatus.textContent = 'Sim: connected';
                
                // Send initial design
                this.sendDesignToPreview();
                break;
                
            case 'disconnected':
                this.previewConnected = false;
                previewBtn.textContent = '▶ Preview';
                previewBtn.classList.remove('active');
                this.updateStatus(null, 'Preview disconnected');
                if (simStatus) simStatus.textContent = 'Sim: —';
                break;
                
            case 'error':
                this.previewConnected = false;
                previewBtn.textContent = '▶ Preview (Error)';
                previewBtn.classList.remove('active');
                this.updateStatus(null, 'Preview connection error');
                if (simStatus) simStatus.textContent = 'Sim: error';
                break;
                
            case 'failed':
                this.previewConnected = false;
                previewBtn.textContent = '▶ Preview (Failed)';
                previewBtn.classList.remove('active');
                this.updateStatus(null, 'Preview connection failed');
                if (simStatus) simStatus.textContent = 'Sim: failed';
                break;
        }
    }

    /**
     * Send current design to preview
     */
    sendDesignToPreview() {
        if (!this.previewClient || !this.previewConnected) {
            return;
        }
        
        const design = {
            canvas: {
                width: 128,
                height: 64
            },
            widgets: Array.from(this.renderer.widgets.values())
        };
        
        this.previewClient.sendDesign(design);
        console.log('[App] Sent design to preview');
    }

    /** Update simulator status panel */
    updateSimulatorStatus(simState) {
        const el = document.getElementById('sim-status');
        if (!el) return;
        if (!this.previewConnected) {
            el.textContent = 'Sim: —';
            return;
        }
        const btnA = simState.buttons?.A ? 'A' : 'a';
        const btnB = simState.buttons?.B ? 'B' : 'b';
        const btnC = simState.buttons?.C ? 'C' : 'c';
        const scene = simState.scene === null ? '?' : simState.scene;
        el.textContent = `Sim: S${scene} [${btnA}${btnB}${btnC}]`;
    }

    async init() {
        console.log('[App] Initializing...');
        
        // Auto-connect with default credentials (skip modal)
        const defaultUsername = 'User-' + Math.random().toString(36).slice(2, 7);
        const defaultProject = 'demo_project';
        this.connect(defaultUsername, defaultProject);
    }

    /**
     * Show join modal to get username and project ID
     */
    showJoinModal() {
        const modal = document.getElementById('join-modal');
        const form = document.getElementById('join-form');
        
        modal.classList.add('show');
        
        form.onsubmit = (e) => {
            e.preventDefault();
            const username = document.getElementById('username-input').value.trim();
            const projectId = document.getElementById('project-input').value.trim();
            
            if (!username || !projectId) {
                alert('Please enter both username and project ID');
                return;
            }
            
            modal.classList.remove('show');
            this.connect(username, projectId);
        };
    }

    /**
     * Connect to WebSocket and initialize modules
     */
    connect(username, projectId) {
        console.log('[App] Connecting as', username, 'to project', projectId);
        
        // Update header
        document.getElementById('project-name').textContent = `Project: ${projectId}`;
        
        // Initialize WebSocket
        const wsUrl = `ws://localhost:8000/ws/projects/${projectId}`;
        this.ws = new WebSocketClient(wsUrl);
        
        // Initialize renderer
        const canvas = document.getElementById('canvas');
        this.renderer = new CanvasRenderer(canvas);
        
        // Initialize undo/redo UI
        this.undoRedoUI = new UndoRedoUI(this.ws, this.renderer);
        
        // Initialize properties editor
        this.propertiesEditor = new PropertiesEditor(this.ws, this.renderer);
        
        // Setup WebSocket event handlers
        this.setupWebSocketHandlers();
        
        // Setup UI event handlers
        this.setupUIHandlers();
        
        // Setup canvas interaction
        this.setupCanvasInteraction();

        // Setup global shortcuts
        this.setupGlobalShortcuts();
        
        // Connect WebSocket
        this.ws.connect();
        
        // Join session after connection
        this.ws.on('connected', () => {
            this.ws.join(projectId, username);
            this.updateStatus(true);
            
            // Auto-start preview after 1 second
            setTimeout(() => {
                if (!this.previewConnected) {
                    console.log('[App] Auto-starting preview...');
                    this.togglePreview();
                }
            }, 1000);
        });
        
        this.ws.on('disconnected', () => {
            this.updateStatus(false);
        });
    }

    /**
     * Setup WebSocket event handlers
     */
    setupWebSocketHandlers() {
        // Session state (initial data)
        this.ws.on('session_state', (msg) => {
            console.log('[App] Session state:', msg);
            
            // Load widgets
            if (msg.design?.widgets) {
                this.renderer.clearWidgets();
                for (const widget of msg.design.widgets) {
                    this.renderer.addWidget(widget.id, widget);
                }
            }

            // Set my user id and render current users
            if (msg.user_id) {
                this.ws.userId = msg.user_id;
            }
            if (Array.isArray(msg.session?.users)) {
                const userList = document.getElementById('user-list');
                userList.innerHTML = '';
                for (const u of msg.session.users) {
                    // Backend users have fields id and name
                    this.addUserBadge(u.id, u.name);
                }
            }
        });

        // User joined
        this.ws.on('user_joined', (msg) => {
            console.log('[App] User joined:', msg);
            // Backend sends { user: { id, name } }
            const u = msg.user || {};
            if (u.id) {
                this.addUserBadge(u.id, u.name || `User ${u.id.substring(0,4)}`);
            }
        });

        // User left
        this.ws.on('user_left', (msg) => {
            console.log('[App] User left:', msg);
            this.removeUserBadge(msg.user_id);
            this.removeCursor(msg.user_id);
        });

        // Cursor update
        this.ws.on('cursor', (msg) => {
            if (msg.user_id !== this.ws.userId) {
                this.updateCursor(msg.user_id, msg.username || msg.name || msg.user_name || msg.user_id, msg.x, msg.y, msg.color);
            }
        });

        // Widget added
        this.ws.on('widget_add', (msg) => {
            console.log('[App] Widget added:', msg);
            this.renderer.addWidget(msg.widget.id, msg.widget);
        });

        // Widget updated
        this.ws.on('widget_update', (msg) => {
            console.log('[App] Widget updated:', msg);
            const changes = msg.changes || msg.updates || {};
            this.renderer.updateWidget(msg.widget_id, changes);
            this.propertiesEditor.onWidgetUpdated(msg.widget_id, changes);
        });

        // Widget deleted
        this.ws.on('widget_delete', (msg) => {
            console.log('[App] Widget deleted:', msg);
            this.renderer.deleteWidget(msg.widget_id);
            this.propertiesEditor.onWidgetDeleted(msg.widget_id);
        });
    }

    /**
     * Setup UI event handlers (toolbar, etc.)
     */
    setupUIHandlers() {
        // Zoom controls
        document.getElementById('zoom-in-btn').addEventListener('click', () => {
            this.renderer.zoomIn();
            this.updateCanvasInfo();
        });

        document.getElementById('zoom-out-btn').addEventListener('click', () => {
            this.renderer.zoomOut();
            this.updateCanvasInfo();
        });

        document.getElementById('zoom-reset-btn').addEventListener('click', () => {
            this.renderer.resetZoom();
            this.updateCanvasInfo();
        });

        // Zoom to fit
        const zoomFitBtn = document.getElementById('zoom-fit-btn');
        if (zoomFitBtn) {
            zoomFitBtn.addEventListener('click', () => this.zoomToFit());
        }

        // Grid toggle
        document.getElementById('grid-btn').addEventListener('click', (e) => {
            const enabled = this.renderer.toggleGrid();
            e.target.classList.toggle('active', enabled);
        });

        // Grid size selector
        const gridSize = document.getElementById('grid-size-select');
        if (gridSize) {
            gridSize.addEventListener('change', () => {
                this.renderer.setGridSize(gridSize.value);
            });
        }

        // Z-order controls
        const bringFront = document.getElementById('bring-front-btn');
        const sendBack = document.getElementById('send-back-btn');
        if (bringFront) bringFront.addEventListener('click', () => {
            const id = this.renderer.selectedWidget;
            if (id) this.renderer.moveToFront(id);
        });
        if (sendBack) sendBack.addEventListener('click', () => {
            const id = this.renderer.selectedWidget;
            if (id) this.renderer.moveToBack(id);
        });

        // Widget toolbox drag & drop
        for (const item of document.querySelectorAll('.widget-item')) {
            item.addEventListener('dragstart', (e) => {
                const type = item.dataset.type;
                e.dataTransfer.setData('widget-type', type);
                console.log('[App] Drag start:', type);
            });
        }

        // Export button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.showExportDialog());
        }

        // Auto-save to localStorage every 30 seconds
        this.autoSaveInterval = setInterval(() => this.autoSave(), 30000);

            // Preview button
            const previewBtn = document.getElementById('previewBtn');
            if (previewBtn) {
                previewBtn.addEventListener('click', () => this.togglePreview());
            }
    }

    /**
     * Setup canvas interaction (click, drag, drop)
     */
    setupCanvasInteraction() {
        const canvas = this.renderer.canvas;
        const overlay = document.getElementById('cursors');
        let marquee = null; // DOM element for selection rectangle
        let marqueeStart = null; // {sx, sy} in screen coords
        
        // Click to select widget
        canvas.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const sx = e.clientX - rect.left;
            const sy = e.clientY - rect.top;

            // Middle mouse button or Space+drag for panning
            if (e.button === 1 || (e.button === 0 && this.spacePressed)) {
                this.panState = {
                    startX: e.clientX,
                    startY: e.clientY,
                    startPanX: this.renderer.panX,
                    startPanY: this.renderer.panY
                };
                canvas.style.cursor = 'grabbing';
                globalThis.addEventListener('mousemove', this.onPanMove);
                globalThis.addEventListener('mouseup', this.onPanEnd, { once: true });
                return;
            }

            // Check for group resize handle first (if multiple selected)
            const groupHandle = this.getGroupHandleAtScreen(sx, sy);
            if (groupHandle) {
                canvas.style.cursor = this.getResizeCursor(groupHandle);
                const groupIds = Array.from(this.renderer.selectedWidgets);
                const groupRect = this.renderer.getBoundingBox(groupIds);
                const startCanvas = this.renderer.screenToCanvas(e.clientX, e.clientY);
                const startRects = {};
                for (const id of groupIds) {
                    const w0 = this.renderer.widgets.get(id);
                    if (w0) startRects[id] = { x: w0.x, y: w0.y, w: w0.width, h: w0.height };
                }
                this.dragState = {
                    mode: 'group-resize',
                    handle: groupHandle,
                    groupIds,
                    startRects,
                    startCanvas,
                    startGroupRect: { ...groupRect }
                };
                globalThis.addEventListener('mousemove', this.onDragMove);
                globalThis.addEventListener('mouseup', this.onDragEnd, { once: true });
                return;
            }

            const widgetId = this.renderer.getWidgetAt(sx, sy);
            if (widgetId) {
                // Shift-click toggles selection (multi-select)
                let widget;
                if (e.shiftKey) {
                    this.renderer.toggleSelection(widgetId);
                    const selected = this.renderer.widgets.get(widgetId);
                    widget = selected;
                } else {
                    widget = this.renderer.selectWidget(widgetId);
                }
                this.propertiesEditor.showWidget(widgetId, widget);

                // Determine if resizing via handle or moving
                const handle = this.getHandleAtScreen(widget, sx, sy);
                const startCanvas = this.renderer.screenToCanvas(e.clientX, e.clientY);
                const selectedWidgets = this.renderer.selectedWidgets;
                const isGroupMove = !handle && selectedWidgets?.has(widgetId) && selectedWidgets.size > 1;
                
                // Set cursor style
                if (handle) {
                    canvas.style.cursor = this.getResizeCursor(handle);
                } else if (isGroupMove) {
                    canvas.style.cursor = 'move';
                } else {
                    canvas.style.cursor = 'move';
                }
                
                let startRects = null;
                let groupIds = null;
                if (isGroupMove) {
                    groupIds = Array.from(this.renderer.selectedWidgets);
                    startRects = {};
                    for (const id of groupIds) {
                        const w0 = this.renderer.widgets.get(id);
                        if (w0) startRects[id] = { x: w0.x, y: w0.y, w: w0.width, h: w0.height };
                    }
                }
                let mode = 'move';
                if (handle) {
                    mode = 'resize';
                } else if (isGroupMove) {
                    mode = 'group-move';
                }

                this.dragState = {
                    mode,
                    handle,
                    widgetId,
                    groupIds,
                    startRects,
                    startCanvas,
                    startRect: { x: widget.x, y: widget.y, w: widget.width, h: widget.height }
                };
                // Attach move/up listeners on window to track outside canvas
                globalThis.addEventListener('mousemove', this.onDragMove);
                globalThis.addEventListener('mouseup', this.onDragEnd, { once: true });
            } else {
                // Start marquee selection
                this.renderer.clearSelection();
                this.propertiesEditor.clear();
                marqueeStart = { sx, sy };
                marquee = document.createElement('div');
                marquee.className = 'marquee-box';
                marquee.style.left = `${sx}px`;
                marquee.style.top = `${sy}px`;
                marquee.style.width = '0px';
                marquee.style.height = '0px';
                overlay.appendChild(marquee);

                const onMove = (ev) => {
                    const rx = ev.clientX - rect.left;
                    const ry = ev.clientY - rect.top;
                    const x = Math.min(marqueeStart.sx, rx);
                    const y = Math.min(marqueeStart.sy, ry);
                    const w = Math.abs(rx - marqueeStart.sx);
                    const h = Math.abs(ry - marqueeStart.sy);
                    marquee.style.left = `${x}px`;
                    marquee.style.top = `${y}px`;
                    marquee.style.width = `${w}px`;
                    marquee.style.height = `${h}px`;

                    // Convert to canvas coords and update selection
                    const p1 = this.renderer.screenToCanvas(x + rect.left, y + rect.top);
                    const p2 = this.renderer.screenToCanvas(x + w + rect.left, y + h + rect.top);
                    const selRect = { x: Math.min(p1.x, p2.x), y: Math.min(p1.y, p2.y), width: Math.abs(p2.x - p1.x), height: Math.abs(p2.y - p1.y) };
                    const inside = [];
                    for (const [id, wgt] of this.renderer.widgets) {
                        if (this.rectsIntersect(selRect, { x: wgt.x, y: wgt.y, width: wgt.width, height: wgt.height })) {
                            inside.push(id);
                        }
                    }
                    this.renderer.setSelection(inside);
                };

                const onUp = () => {
                    globalThis.removeEventListener('mousemove', onMove);
                    globalThis.removeEventListener('mouseup', onUp);
                    if (marquee) marquee.remove();
                    marquee = null;
                    marqueeStart = null;
                };

                globalThis.addEventListener('mousemove', onMove);
                globalThis.addEventListener('mouseup', onUp, { once: true });
            }
        });

        // Double-click to edit widget text
        canvas.addEventListener('dblclick', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const sx = e.clientX - rect.left;
            const sy = e.clientY - rect.top;
            const widgetId = this.renderer.getWidgetAt(sx, sy);
            if (widgetId) {
                const widget = this.renderer.widgets.get(widgetId);
                if (widget) {
                    const newText = prompt(`Edit text for ${widget.type}:`, widget.text || '');
                    if (newText !== null) {
                        this.renderer.updateWidget(widgetId, { text: newText });
                        this.ws.updateWidget(widgetId, { text: newText });
                        if (this.previewConnected) {
                            this.sendDesignToPreview();
                        }
                        this.propertiesEditor.onWidgetUpdated(widgetId, { text: newText });
                    }
                }
            }
        });

        // Mouse move for cursor tracking
        let cursorThrottle = null;
        let lastHoveredWidget = null;
        canvas.addEventListener('mousemove', (e) => {
            // Cursor broadcast
            const { x, y } = this.renderer.screenToCanvas(e.clientX, e.clientY);
            if (!cursorThrottle) {
                cursorThrottle = setTimeout(() => {
                    this.ws.sendCursor(Math.round(x), Math.round(y));
                    cursorThrottle = null;
                }, 50);
            }

            // If dragging, let window handler process movement
            if (this.dragState || this.panState) return;

            // Show widget info on hover
            const rect = canvas.getBoundingClientRect();
            const sx = e.clientX - rect.left;
            const sy = e.clientY - rect.top;
            const widgetId = this.renderer.getWidgetAt(sx, sy);
            if (widgetId && widgetId !== lastHoveredWidget) {
                lastHoveredWidget = widgetId;
                const widget = this.renderer.widgets.get(widgetId);
                if (widget) {
                    canvas.title = `${widget.type} - ${widget.width}×${widget.height} @ (${widget.x}, ${widget.y})`;
                }
            } else if (!widgetId && lastHoveredWidget) {
                lastHoveredWidget = null;
                canvas.title = '';
            }

            // Update canvas info
            this.updateCanvasInfo();
        });

        // Drop widget from toolbox
        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            
            const type = e.dataTransfer.getData('widget-type');
            if (!type) return;
            
            const { x, y } = this.renderer.screenToCanvas(e.clientX, e.clientY);
            
            const widget = this.createWidget(type, Math.round(x), Math.round(y));
            console.log('[App] Drop widget:', widget);
            // Apply locally for immediate feedback (server does not echo sender)
            this.renderer.addWidget(widget.id, widget);
            this.renderer.selectWidget(widget.id);
            this.propertiesEditor.showWidget(widget.id, widget);
            this.ws.addWidget(widget);
            
                    // Send to preview if connected
                    if (this.previewConnected) {
                        this.sendDesignToPreview();
                    }
        });

        // Ctrl+wheel zoom at cursor
        canvas.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                const factor = e.deltaY < 0 ? 1.1 : 0.9;
                this.applyZoomAt(e.clientX, e.clientY, factor);
            }
        }, { passive: false });
    }

    // Bound handlers to keep 'this'
    onDragMove = (e) => {
        if (!this.dragState) return;
        e.preventDefault();
        const { x: cx, y: cy } = this.renderer.screenToCanvas(e.clientX, e.clientY);
        const grid = this.renderer.showGrid ? 10 : 1;

        const ds = this.dragState;

        const dx = cx - ds.startCanvas.x;
        const dy = cy - ds.startCanvas.y;

        // Group resize: apply proportional scaling to all selected widgets
        if (ds.mode === 'group-resize' && ds.groupIds && ds.startRects && ds.startGroupRect) {
            const gr = ds.startGroupRect;
            let newGX = gr.x, newGY = gr.y, newGW = gr.width, newGH = gr.height;
            
            switch (ds.handle) {
                case 'tl':
                    newGX = this.snap(gr.x + dx, grid);
                    newGY = this.snap(gr.y + dy, grid);
                    newGW = this.snap(gr.width - dx, grid);
                    newGH = this.snap(gr.height - dy, grid);
                    break;
                case 'tr':
                    newGY = this.snap(gr.y + dy, grid);
                    newGW = this.snap(gr.width + dx, grid);
                    newGH = this.snap(gr.height - dy, grid);
                    break;
                case 'bl':
                    newGX = this.snap(gr.x + dx, grid);
                    newGW = this.snap(gr.width - dx, grid);
                    newGH = this.snap(gr.height + dy, grid);
                    break;
                case 'br':
                    newGW = this.snap(gr.width + dx, grid);
                    newGH = this.snap(gr.height + dy, grid);
                    break;
            }
            newGW = Math.max(20, newGW);
            newGH = Math.max(20, newGH);
            
            
            for (const id of ds.groupIds) {
                const s = ds.startRects[id];
                if (!s) continue;
                const relX = (s.x - gr.x) / gr.width;
                const relY = (s.y - gr.y) / gr.height;
                const relW = s.w / gr.width;
                const relH = s.h / gr.height;
                const nx = newGX + relX * newGW;
                const ny = newGY + relY * newGH;
                const nw = Math.max(10, relW * newGW);
                const nh = Math.max(10, relH * newGH);
                this.renderer.updateWidget(id, { x: nx, y: ny, width: nw, height: nh });
                this.propertiesEditor.onWidgetUpdated(id, { x: nx, y: ny, width: nw, height: nh });
            }

            // No intermediate WS updates during drag - only at drag end
            return;
        }

        // Group move: apply delta to all selected
        if (ds.mode === 'group-move' && ds.groupIds && ds.startRects) {
            const updates = {};
            for (const id of ds.groupIds) {
                const s = ds.startRects[id];
                if (!s) continue;
                const nx = this.snap(s.x + dx, grid);
                const ny = this.snap(s.y + dy, grid);
                updates[id] = { x: nx, y: ny };
                this.renderer.updateWidget(id, { x: nx, y: ny });
                this.propertiesEditor.onWidgetUpdated(id, { x: nx, y: ny });
            }

            // No intermediate WS updates during drag - only at drag end
            return;
        }

        const w = this.renderer.widgets.get(ds.widgetId);
        if (!w) return;

        let nx = ds.startRect.x;
        let ny = ds.startRect.y;
        let nw = ds.startRect.w;
        let nh = ds.startRect.h;

        if (ds.mode === 'move') {
            nx = this.snap(ds.startRect.x + dx, grid);
            ny = this.snap(ds.startRect.y + dy, grid);
            // Snap to other widgets' edges/centers
            const snapped = this.computeSnap(nx, ny, nw, nh, ds.widgetId);
            nx += snapped.dx;
            ny += snapped.dy;
            this.showGuides(snapped);
        } else {
            // resize
            switch (ds.handle) {
                case 'tl':
                    nx = this.snap(ds.startRect.x + dx, grid);
                    ny = this.snap(ds.startRect.y + dy, grid);
                    nw = this.snap(ds.startRect.w - dx, grid);
                    nh = this.snap(ds.startRect.h - dy, grid);
                    break;
                case 'tr':
                    ny = this.snap(ds.startRect.y + dy, grid);
                    nw = this.snap(ds.startRect.w + dx, grid);
                    nh = this.snap(ds.startRect.h - dy, grid);
                    break;
                case 'bl':
                    nx = this.snap(ds.startRect.x + dx, grid);
                    nw = this.snap(ds.startRect.w - dx, grid);
                    nh = this.snap(ds.startRect.h + dy, grid);
                    break;
                case 'br':
                    nw = this.snap(ds.startRect.w + dx, grid);
                    nh = this.snap(ds.startRect.h + dy, grid);
                    break;
            }
            nw = Math.max(10, nw);
            nh = Math.max(10, nh);
            // Simple snap for resizing: adjust side deltas
            const snapped = this.computeSnap(nx, ny, nw, nh, ds.widgetId, ds.handle);
            nx += snapped.dx;
            ny += snapped.dy;
            nw += snapped.dw || 0;
            nh += snapped.dh || 0;
            this.showGuides(snapped);
        }

        this.renderer.updateWidget(ds.widgetId, { x: nx, y: ny, width: nw, height: nh });
        this.propertiesEditor.onWidgetUpdated(ds.widgetId, { x: nx, y: ny, width: nw, height: nh });

        // No intermediate WS updates during drag - only at drag end
    };

    onDragEnd = (e) => {
        if (!this.dragState) return;
        e.preventDefault();
        const ds = this.dragState;
        // Send final updates for moved items
        if ((ds.mode === 'group-move' || ds.mode === 'group-resize') && ds.groupIds) {
            for (const id of ds.groupIds) {
                const w = this.renderer.widgets.get(id);
                if (w) this.ws.updateWidget(id, { x: w.x, y: w.y, width: w.width, height: w.height });
            }
            // Send to preview after group operations
            if (this.previewConnected) {
                this.sendDesignToPreview();
            }
        } else {
            const id = ds.widgetId;
            const w = this.renderer.widgets.get(id);
            if (w) {
                this.ws.updateWidget(id, { x: w.x, y: w.y, width: w.width, height: w.height });
                // Send to preview after single widget update
                if (this.previewConnected) {
                    this.sendDesignToPreview();
                }
            }
        }
        this.dragState = null;
        this.renderer.canvas.style.cursor = 'default';
        globalThis.removeEventListener('mousemove', this.onDragMove);
        this.clearGuides();
    };

    onPanMove = (e) => {
        if (!this.panState) return;
        e.preventDefault();
        const dx = e.clientX - this.panState.startX;
        const dy = e.clientY - this.panState.startY;
        this.renderer.panX = this.panState.startPanX + dx;
        this.renderer.panY = this.panState.startPanY + dy;
        this.renderer.render();
    };

    onPanEnd = (e) => {
        if (!this.panState) return;
        e.preventDefault();
        this.panState = null;
        this.renderer.canvas.style.cursor = this.spacePressed ? 'grab' : 'default';
        globalThis.removeEventListener('mousemove', this.onPanMove);
    };

    snap(v, grid) {
        if (grid <= 1) return v;
        return Math.round(v / grid) * grid;
    }

    getResizeCursor(handle) {
        const cursors = {
            'tl': 'nwse-resize',
            'tr': 'nesw-resize',
            'bl': 'nesw-resize',
            'br': 'nwse-resize'
        };
        return cursors[handle] || 'default';
    }

    getHandleAtScreen(widget, sx, sy) {
        const hs = 6; // base handle size in canvas units
        const z = this.renderer.zoom;
        const px = this.renderer.panX;
        const py = this.renderer.panY;
        const handles = [
            { name: 'tl', x: widget.x, y: widget.y },
            { name: 'tr', x: widget.x + widget.width, y: widget.y },
            { name: 'bl', x: widget.x, y: widget.y + widget.height },
            { name: 'br', x: widget.x + widget.width, y: widget.y + widget.height },
        ];
        const half = (hs / 2) * z + 3; // clickable tolerance in screen px
        for (const h of handles) {
            const hx = h.x * z + px;
            const hy = h.y * z + py;
            if (Math.abs(sx - hx) <= half && Math.abs(sy - hy) <= half) {
                return h.name;
            }
        }
        return null;
    }

    getGroupHandleAtScreen(sx, sy) {
        if (this.renderer.selectedWidgets.size < 2) return null;
        const rect = this.renderer.getBoundingBox(Array.from(this.renderer.selectedWidgets));
        if (!rect) return null;
        const hs = 8; // group handle size in canvas units
        const z = this.renderer.zoom;
        const px = this.renderer.panX;
        const py = this.renderer.panY;
        const handles = [
            { name: 'tl', x: rect.x, y: rect.y },
            { name: 'tr', x: rect.x + rect.width, y: rect.y },
            { name: 'bl', x: rect.x, y: rect.y + rect.height },
            { name: 'br', x: rect.x + rect.width, y: rect.y + rect.height },
        ];
        const half = (hs / 2) * z + 4;
        for (const h of handles) {
            const hx = h.x * z + px;
            const hy = h.y * z + py;
            if (Math.abs(sx - hx) <= half && Math.abs(sy - hy) <= half) {
                return h.name;
            }
        }
        return null;
    }

    setupGlobalShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete') {
                const id = this.renderer.selectedWidget;
                if (id) {
                    e.preventDefault();
                    this.ws.deleteWidget(id);
                                        if (this.previewConnected) {
                                            this.sendDesignToPreview();
                                        }
                    this.renderer.deleteWidget(id);
                    this.propertiesEditor.clear();
                }
            }

            // Nudge with arrows (Shift = 10x)
            const id = this.renderer.selectedWidget;
            if (id && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)) {
                e.preventDefault();
                const step = e.shiftKey ? 10 : 1;
                let dx = 0, dy = 0;
                if (e.key === 'ArrowUp') dy = -step;
                if (e.key === 'ArrowDown') dy = step;
                if (e.key === 'ArrowLeft') dx = -step;
                if (e.key === 'ArrowRight') dx = step;
                const w = this.renderer.widgets.get(id);
                if (w) {
                    const nx = w.x + dx;
                    const ny = w.y + dy;
                    this.renderer.updateWidget(id, { x: nx, y: ny });
                    this.ws.updateWidget(id, { x: nx, y: ny });
                                        if (this.previewConnected) {
                                            this.sendDesignToPreview();
                                        }
                    this.propertiesEditor.onWidgetUpdated(id, { x: nx, y: ny });
                }
            }

            // Duplicate selection Ctrl+D
            if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'd')) {
                const id = this.renderer.selectedWidget;
                if (id) {
                    e.preventDefault();
                    const w = this.renderer.widgets.get(id);
                    if (w) {
                        const newWidget = {
                            ...w,
                            id: `widget-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                            x: w.x + 10,
                            y: w.y + 10
                        };
                        // Add locally for instant feedback
                        this.renderer.addWidget(newWidget.id, newWidget);
                        // Broadcast
                        this.ws.addWidget(newWidget);
                        // Select duplicate
                        this.renderer.selectWidget(newWidget.id);
                        this.propertiesEditor.showWidget(newWidget.id, newWidget);
                        if (this.previewConnected) {
                            this.sendDesignToPreview();
                        }
                    }
                }
            }

            // Copy Ctrl+C
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c') {
                const id = this.renderer.selectedWidget;
                if (id) {
                    e.preventDefault();
                    const w = this.renderer.widgets.get(id);
                    if (w) {
                        this.clipboard = { ...w };
                        console.log('[App] Copied widget to clipboard:', this.clipboard);
                    }
                }
            }

            // Paste Ctrl+V
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v') {
                if (this.clipboard) {
                    e.preventDefault();
                    const newWidget = {
                        ...this.clipboard,
                        id: `widget-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                        x: this.clipboard.x + 15,
                        y: this.clipboard.y + 15
                    };
                    this.renderer.addWidget(newWidget.id, newWidget);
                    this.ws.addWidget(newWidget);
                    this.renderer.selectWidget(newWidget.id);
                    this.propertiesEditor.showWidget(newWidget.id, newWidget);
                    console.log('[App] Pasted widget from clipboard:', newWidget);
                }
            }

            // Select All Ctrl+A
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
                e.preventDefault();
                const allIds = Array.from(this.renderer.widgets.keys());
                if (allIds.length > 0) {
                    this.renderer.setSelection(allIds);
                    console.log('[App] Selected all widgets:', allIds.length);
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.key === ' ') {
                this.spacePressed = false;
                if (this.renderer?.canvas && !this.panState) {
                    this.renderer.canvas.style.cursor = 'default';
                }
            }
        });
    }

    zoomToFit() {
        // Prefer selection rect if available
        const id = this.renderer.selectedWidget;
        let rect = null;
        if (id) {
            rect = this.renderer.getBoundingBox([id]);
        } else {
            rect = this.renderer.getBoundingBox();
        }
        this.renderer.zoomToRect(rect, 20);
        this.updateCanvasInfo();
    }

    computeSnap(nx, ny, nw, nh, movingId, handle = null) {
        const threshold = 5; // px in canvas coords
        const edges = {
            l: nx, cX: nx + nw / 2, r: nx + nw,
            t: ny, cY: ny + nh / 2, b: ny + nh
        };
        let bestDx = 0, bestDy = 0, minDx = threshold + 1, minDy = threshold + 1;
        let adjW = 0, adjH = 0;
        let guideX = null, guideY = null;
        for (const [id, w] of this.renderer.widgets) {
            if (id === movingId) continue;
            const wEdges = {
                l: w.x, cX: w.x + w.width / 2, r: w.x + w.width,
                t: w.y, cY: w.y + w.height / 2, b: w.y + w.height
            };
            // X axis: l/cX/r vs target l/cX/r
            for (const key of ['l','cX','r']) {
                const targets = [wEdges.l, wEdges.cX, wEdges.r];
                for (const t of targets) {
                    const d = Math.abs(edges[key] - t);
                    if (d < minDx && d <= threshold) {
                        minDx = d;
                        const delta = t - edges[key];
                        if (handle && (handle === 'tl' || handle === 'bl')) {
                            bestDx = delta; adjW = -delta; // adjust left, shrink/grow width
                        } else if (handle && (handle === 'tr' || handle === 'br')) {
                            bestDx = 0; adjW = delta; // adjust right via width
                        } else {
                            bestDx = delta; adjW = 0;
                        }
                        guideX = t;
                    }
                }
            }
            // Y axis: t/cY/b vs target t/cY/b
            for (const key of ['t','cY','b']) {
                const targets = [wEdges.t, wEdges.cY, wEdges.b];
                for (const t of targets) {
                    const d = Math.abs(edges[key] - t);
                    if (d < minDy && d <= threshold) {
                        minDy = d;
                        const delta = t - edges[key];
                        if (handle && (handle === 'tl' || handle === 'tr')) {
                            bestDy = delta; adjH = -delta;
                        } else if (handle && (handle === 'bl' || handle === 'br')) {
                            bestDy = 0; adjH = delta;
                        } else {
                            bestDy = delta; adjH = 0;
                        }
                        guideY = t;
                    }
                }
            }
        }
        return { dx: bestDx, dy: bestDy, dw: adjW, dh: adjH, guideX, guideY };
    }

    // Show alignment guides in overlay
    showGuides(snapped) {
        const overlay = document.getElementById('cursors');
        this.clearGuides();
        const z = this.renderer.zoom;
        const px = this.renderer.panX;
        const py = this.renderer.panY;
        if (snapped.guideX !== null && snapped.guideX !== undefined) {
            const v = document.createElement('div');
            v.className = 'guide-line v';
            v.style.left = `${snapped.guideX * z + px}px`;
            v.style.top = `0`;
            v.style.height = `${this.renderer.canvas.offsetHeight}px`;
            overlay.appendChild(v);
        }
        if (snapped.guideY !== null && snapped.guideY !== undefined) {
            const h = document.createElement('div');
            h.className = 'guide-line h';
            h.style.top = `${snapped.guideY * z + py}px`;
            h.style.left = `0`;
            h.style.width = `${this.renderer.canvas.offsetWidth}px`;
            overlay.appendChild(h);
        }
    }

    clearGuides() {
        const overlay = document.getElementById('cursors');
        for (const el of overlay.querySelectorAll('.guide-line')) {
            el.remove();
        }
    }

    rectsIntersect(a, b) {
        return !(a.x + a.width < b.x || b.x + b.width < a.x || a.y + a.height < b.y || b.y + b.height < a.y);
    }

    applyZoomAt(screenX, screenY, factor) {
        // Convert screen to canvas coords before zoom
        const before = this.renderer.screenToCanvas(screenX, screenY);
        // Apply zoom
        const newZoom = Math.max(0.1, Math.min(5, this.renderer.zoom * factor));
        this.renderer.zoom = newZoom;
        // Adjust pan so the point under cursor stays
        this.renderer.panX = screenX - before.x * newZoom;
        this.renderer.panY = screenY - before.y * newZoom;
        this.renderer.render();
        this.updateCanvasInfo();
    }

    /**
     * Create new widget of given type
     */
    createWidget(type, x, y) {
        const id = `widget-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
        
        const defaults = {
            label: { width: 100, height: 30, text: 'Label' },
            button: { width: 100, height: 40, text: 'Button' },
            checkbox: { width: 80, height: 30, text: 'Checkbox' },
            slider: { width: 150, height: 30, text: '' },
            input: { width: 150, height: 35, text: '' },
            panel: { width: 200, height: 150, text: '', color: '#2d2d30' },
            list: { width: 200, height: 200, text: '', color: '#252526' }
        };

        const props = defaults[type] || { width: 100, height: 50, text: type };

        return {
            id,
            type,
            x,
            y,
            ...props
        };
    }

    /**
     * Update cursor position for remote user
     */
    updateCursor(userId, username, x, y, color) {
        let cursor = this.cursors.get(userId);
        
        if (!cursor) {
            cursor = document.createElement('div');
            cursor.className = 'remote-cursor';
            cursor.style.color = color || this.getUserColor(userId);
            cursor.innerHTML = `
                <div class="cursor-pointer"></div>
                <div class="cursor-label">${username}</div>
            `;
            document.getElementById('cursors').appendChild(cursor);
            this.cursors.set(userId, cursor);
        }
        
        // Transform canvas coords to screen coords
        const screenX = x * this.renderer.zoom + this.renderer.panX;
        const screenY = y * this.renderer.zoom + this.renderer.panY;
        
        cursor.style.left = screenX + 'px';
        cursor.style.top = screenY + 'px';
    }

    /**
     * Remove cursor for user
     */
    removeCursor(userId) {
        const cursor = this.cursors.get(userId);
        if (cursor) {
            cursor.remove();
            this.cursors.delete(userId);
        }
    }

    /**
     * Add user badge to header
     */
    addUserBadge(userId, username) {
        const userList = document.getElementById('user-list');
        const isMe = userId === this.ws.userId;
        
        const badge = document.createElement('div');
        badge.className = 'user-badge' + (isMe ? ' you' : '');
        badge.dataset.userId = userId;
        
        const color = this.getUserColor(userId);
        badge.innerHTML = `
            <span class="user-avatar" style="background-color: ${color}">
                ${username}${isMe ? ' (You)' : ''}
            </span>
        `;
        
        userList.appendChild(badge);
    }

    /**
     * Remove user badge
     */
    removeUserBadge(userId) {
        const badge = document.querySelector(`.user-badge[data-user-id="${userId}"]`);
        if (badge) badge.remove();
    }

    /**
     * Get consistent color for user
     */
    getUserColor(userId) {
        const colors = [
            '#f48771', '#4ec9b0', '#ce9178', '#dcdcaa', '#c586c0',
            '#9cdcfe', '#4fc1ff', '#b5cea8', '#d16969'
        ];
        const hash = userId.split('').reduce((acc, c) => acc + (c.codePointAt(0) || 0), 0);
        return colors[hash % colors.length];
    }

    /**
     * Update connection status indicator
     */
    updateStatus(connected) {
        const indicator = document.querySelector('.status-indicator');
        const text = document.getElementById('status-text');
        
        if (connected) {
            indicator.classList.add('connected');
            text.textContent = 'Connected';
        } else {
            indicator.classList.remove('connected');
            text.textContent = 'Disconnected';
        }
    }

    /**
     * Show export dialog
     */
    showExportDialog() {
        const options = prompt('Export options:\n1 - JSON\n2 - PNG\n3 - Both\n\nEnter option (1-3):', '1');
        if (!options) return;

        switch (options.trim()) {
            case '1':
                this.exportJSON();
                break;
            case '2':
                this.exportPNG();
                break;
            case '3':
                this.exportJSON();
                this.exportPNG();
                break;
            default:
                alert('Invalid option');
        }
    }

    /**
     * Export design to JSON
     */
    exportJSON() {
        const design = {
            widgets: Array.from(this.renderer.widgets.values()),
            canvas: {
                width: this.renderer.width,
                height: this.renderer.height,
                zoom: this.renderer.zoom,
                panX: this.renderer.panX,
                panY: this.renderer.panY
            },
            exported: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(design, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `design-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        console.log('[App] Exported JSON:', design);
    }

    /**
     * Export canvas to PNG
     */
    exportPNG() {
        this.renderer.canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `canvas-${Date.now()}.png`;
            a.click();
            URL.revokeObjectURL(url);
            console.log('[App] Exported PNG');
        });
    }

    /**
     * Auto-save to localStorage
     */
    autoSave() {
        if (!this.ws?.userId) return;
        const key = `esp32os-design-autosave-${this.ws.userId}`;
        const design = {
            widgets: Array.from(this.renderer.widgets.values()),
            timestamp: Date.now()
        };
        try {
            localStorage.setItem(key, JSON.stringify(design));
            console.log('[App] Auto-saved to localStorage');
        } catch (e) {
            console.error('[App] Auto-save failed:', e);
        }
    }

    /**
     * Update canvas info display
     */
    updateCanvasInfo() {
        const info = this.renderer.getInfo();
        const selectedCount = this.renderer.selectedWidgets.size;
        let selectionInfo = '';
        if (selectedCount > 0) {
            selectionInfo = `<span style="color: #007acc;">Selected: ${selectedCount}</span>`;
        }
        document.getElementById('canvas-info').innerHTML = `
            <span>Zoom: ${info.zoom}x</span>
            <span>Widgets: ${info.widgets}</span>
            <span>Grid: ${info.grid ? 'On' : 'Off'}</span>
            ${selectionInfo}
        `;
    }
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    globalThis.app = new App();
    globalThis.app.init();
});
