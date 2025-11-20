/**
 * Undo/Redo UI Manager for ESP32OS Collaborative Editor
 * Manages undo/redo buttons, keyboard shortcuts, and history timeline
 */

export class UndoRedoUI {
    constructor(wsClient, renderer) {
        this.ws = wsClient;
        this.renderer = renderer;
        this.history = [];
        this.currentIndex = -1;
        
        this.undoBtn = document.getElementById('undo-btn');
        this.redoBtn = document.getElementById('redo-btn');
        this.historyList = document.getElementById('history-list');

        this.setupEventListeners();
        this.updateButtons();
    }

    setupEventListeners() {
        // Undo button
        this.undoBtn.addEventListener('click', () => this.undo());

        // Redo button
        this.redoBtn.addEventListener('click', () => this.redo());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'z' && !e.shiftKey) {
                    e.preventDefault();
                    this.undo();
                } else if (e.key === 'z' && e.shiftKey || e.key === 'y') {
                    e.preventDefault();
                    this.redo();
                }
            }
        });

        // Listen to history state updates from WebSocket
        this.ws.on('history_state', (msg) => {
            this.updateHistory(msg.history, msg.current_index);
        });
    }

    /**
     * Perform undo
     */
    undo() {
        if (this.currentIndex < 0) return;
        this.ws.undo();
    }

    /**
     * Perform redo
     */
    redo() {
        if (this.currentIndex >= this.history.length - 1) return;
        this.ws.redo();
    }

    /**
     * Update history from server
     */
    updateHistory(history, currentIndex) {
        this.history = history || [];
        this.currentIndex = currentIndex ?? -1;
        this.updateButtons();
        this.renderTimeline();
    }

    /**
     * Update undo/redo button states
     */
    updateButtons() {
        const canUndo = this.currentIndex >= 0;
        const canRedo = this.currentIndex < this.history.length - 1;

        this.undoBtn.disabled = !canUndo;
        this.redoBtn.disabled = !canRedo;

        // Update tooltip/title
        if (canUndo) {
            const op = this.history[this.currentIndex];
            this.undoBtn.title = `Undo: ${this.formatOperation(op)}`;
        } else {
            this.undoBtn.title = 'Undo';
        }

        if (canRedo) {
            const op = this.history[this.currentIndex + 1];
            this.redoBtn.title = `Redo: ${this.formatOperation(op)}`;
        } else {
            this.redoBtn.title = 'Redo';
        }
    }

    /**
     * Render history timeline
     */
    renderTimeline() {
        if (this.history.length === 0) {
            this.historyList.innerHTML = '<div class="history-empty">No history yet</div>';
            return;
        }

        const items = this.history.map((op, index) => {
            const isCurrent = index === this.currentIndex;
            const className = isCurrent ? 'history-item current' : 'history-item';
            const icon = this.getOperationIcon(op);
            const desc = this.formatOperation(op);
            const user = op.user || 'Unknown';

            return `
                <div class="${className}" data-index="${index}">
                    <span class="history-icon">${icon}</span>
                    <div class="history-desc">${desc}</div>
                    <div class="history-user">${user}</div>
                </div>
            `;
        }).join('');

        this.historyList.innerHTML = items;

        // Add click handlers to jump to specific history state
        this.historyList.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const targetIndex = parseInt(item.dataset.index);
                this.jumpToIndex(targetIndex);
            });
        });

        // Scroll current item into view
        const currentItem = this.historyList.querySelector('.history-item.current');
        if (currentItem) {
            currentItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * Jump to specific history index
     */
    jumpToIndex(targetIndex) {
        // Calculate how many undo/redo operations needed
        const diff = targetIndex - this.currentIndex;
        
        if (diff > 0) {
            // Need to redo
            for (let i = 0; i < diff; i++) {
                this.redo();
            }
        } else if (diff < 0) {
            // Need to undo
            for (let i = 0; i < Math.abs(diff); i++) {
                this.undo();
            }
        }
    }

    /**
     * Format operation for display
     */
    formatOperation(op) {
        const type = op.op_type || op.type || 'unknown';
        const data = op.data || {};

        switch (type) {
            case 'widget_add':
                return `Add ${data.type || 'widget'}`;
            case 'widget_update':
                return `Update ${data.widget_id || 'widget'}`;
            case 'widget_delete':
                return `Delete ${data.widget_id || 'widget'}`;
            default:
                return type;
        }
    }

    /**
     * Get icon for operation
     */
    getOperationIcon(op) {
        const type = op.op_type || op.type || 'unknown';
        
        switch (type) {
            case 'widget_add':
                return '➕';
            case 'widget_update':
                return '✏️';
            case 'widget_delete':
                return '🗑️';
            default:
                return '⚙️';
        }
    }

    /**
     * Clear history
     */
    clear() {
        this.history = [];
        this.currentIndex = -1;
        this.updateButtons();
        this.renderTimeline();
    }
}
