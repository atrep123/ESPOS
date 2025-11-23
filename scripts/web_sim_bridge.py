#!/usr/bin/env python3
"""
WebSocket Bridge Server for Live Preview
Connects Web Designer to ESP32 Simulator for real-time preview
"""

import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

try:
    import websockets
except ImportError:
    print("Error: websockets package not found. Install with: pip install websockets")
    sys.exit(1)

# Type-only import to avoid runtime deprecation warnings while keeping static typing
if TYPE_CHECKING:  # pragma: no cover
    from websockets.server import WebSocketServerProtocol  # type: ignore[attr-defined]

from ui_designer import UIDesigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSimBridge:
    """Bridge between Web Designer and ESP32 Simulator"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        # Use protocol type only for static checking; runtime keeps flexibility
        self.designer_clients: Set['WebSocketServerProtocol'] = set()  # type: ignore[name-defined]
        self.simulator_clients: Set['WebSocketServerProtocol'] = set()  # type: ignore[name-defined]
        self.current_design: Optional[Dict[str, Any]] = None
        self.ui_designer = UIDesigner(128, 64)  # Default ESP32 screen size
        
    async def handle_client(self, websocket: 'WebSocketServerProtocol') -> None:  # type: ignore[name-defined]
        """Handle WebSocket connections from both designer and simulator"""
        client_type: Optional[str] = None
        
        try:
            async for message in websocket:
                data: Dict[str, Any] = json.loads(message)
                op: Optional[str] = data.get('op')
                
                # Client identification
                if op == 'register':
                    client_type = data.get('type')  # 'designer' or 'simulator'
                    if client_type == 'designer':
                        self.designer_clients.add(websocket)
                        logger.info(f"Designer client connected from {websocket.remote_address}")
                        # Send current design if available
                        if self.current_design:
                            await websocket.send(json.dumps({
                                'op': 'design_state',
                                'design': self.current_design
                            }))
                    elif client_type == 'simulator':
                        self.simulator_clients.add(websocket)
                        logger.info(f"Simulator client connected from {websocket.remote_address}")
                        # Send current design to new simulator
                        if self.current_design:
                            await self.broadcast_to_simulators({
                                'op': 'design_update',
                                'design': self.convert_to_simulator_format(self.current_design)
                            })
                    
                    await websocket.send(json.dumps({
                        'op': 'registered',
                        'type': client_type,
                        'status': 'connected'
                    }))
                
                # Design updates from web designer
                elif op == 'design_update':
                    logger.info("Received design update from web designer")
                    self.current_design = data.get('design')
                    
                    # Convert and broadcast to simulators
                    sim_format = self.convert_to_simulator_format(self.current_design)
                    await self.broadcast_to_simulators({
                        'op': 'design_update',
                        'design': sim_format
                    })
                    
                    # Echo back to other designers
                    await self.broadcast_to_designers({
                        'op': 'design_synced',
                        'design': self.current_design
                    }, exclude=websocket)
                
                # Widget operations
                elif op == 'widget_add':
                    widget: Dict[str, Any] = data.get('widget', {})
                    if self.current_design is None:
                        self.current_design = {'widgets': []}
                    self.current_design['widgets'].append(widget)
                    
                    await self.broadcast_to_simulators({
                        'op': 'widget_add',
                        'widget': self.convert_widget_to_sim(widget)
                    })
                
                elif op == 'widget_update':
                    widget_id: Any = data.get('widget_id')
                    changes: Dict[str, Any] = data.get('changes', {})
                    
                    if self.current_design:
                        for w in self.current_design['widgets']:
                            if w.get('id') == widget_id:
                                w.update(changes)
                                break
                    
                    await self.broadcast_to_simulators({
                        'op': 'widget_update',
                        'widget_id': widget_id,
                        'changes': changes
                    })
                
                elif op == 'widget_delete':
                    widget_id: Any = data.get('widget_id')
                    
                    if self.current_design:
                        self.current_design['widgets'] = [
                            w for w in self.current_design['widgets']
                            if w.get('id') != widget_id
                        ]
                    
                    await self.broadcast_to_simulators({
                        'op': 'widget_delete',
                        'widget_id': widget_id
                    })
                
                # Simulator feedback (future: interaction events)
                elif op == 'sim_event':
                    event_type: Any = data.get('event_type')
                    event_data: Any = data.get('data')
                    
                    await self.broadcast_to_designers({
                        'op': 'sim_event',
                        'event_type': event_type,
                        'data': event_data
                    })

                # Full design update originating from simulator side
                elif op == 'sim_design_update':
                    scene: Dict[str, Any] = data.get('scene', {})
                    logger.info("Received design update from simulator")
                    web_design = self.convert_from_simulator_format(scene)
                    self.current_design = web_design
                    # Broadcast to designers to sync
                    await self.broadcast_to_designers({
                        'op': 'design_synced',
                        'design': web_design
                    })
                
                else:
                    logger.warning(f"Unknown operation: {op}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            # Cleanup
            if websocket in self.designer_clients:
                self.designer_clients.remove(websocket)
                logger.info("Designer client removed")
            if websocket in self.simulator_clients:
                self.simulator_clients.remove(websocket)
                logger.info("Simulator client removed")
    
    def convert_to_simulator_format(self, design: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert web designer format to simulator format"""
        if not design:
            return {'widgets': []}
        
        widgets = design.get('widgets', [])
        converted_widgets = [self.convert_widget_to_sim(w) for w in widgets]
        
        return {
            'scene': {
                'name': 'live_preview',
                'width': design.get('canvas', {}).get('width', 128),
                'height': design.get('canvas', {}).get('height', 64),
                'widgets': converted_widgets
            }
        }
    
    def convert_widget_to_sim(self, widget: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single widget from web format to simulator format"""
        widget_type = widget.get('type', 'label')
        
        # Map web designer types to simulator WidgetType
        type_mapping = {
            'label': 'LABEL',
            'button': 'BUTTON',
            'checkbox': 'CHECKBOX',
            'slider': 'SLIDER',
            'progressbar': 'PROGRESSBAR',
            'panel': 'PANEL',
            'list': 'LIST',
            'image': 'IMAGE',
            'icon': 'ICON',
            'gauge': 'GAUGE',
            'chart': 'CHART'
        }
        
        sim_widget = {
            'type': type_mapping.get(widget_type, 'LABEL'),
            'x': widget.get('x', 0),
            'y': widget.get('y', 0),
            'width': widget.get('width', 50),
            'height': widget.get('height', 20),
            'text': widget.get('text', ''),
            'id': widget.get('id', ''),
        }
        
        # Additional properties
        if 'color' in widget:
            sim_widget['bg_color'] = widget['color']
        if 'border' in widget:
            sim_widget['border'] = widget['border']
        if 'value' in widget:
            sim_widget['value'] = widget['value']
        if 'checked' in widget:
            sim_widget['checked'] = widget['checked']
        if 'min' in widget:
            sim_widget['min'] = widget['min']
        if 'max' in widget:
            sim_widget['max'] = widget['max']
        if 'items' in widget:
            sim_widget['items'] = widget['items']
        if 'icon' in widget:
            sim_widget['icon'] = widget['icon']
        if 'image' in widget:
            sim_widget['image'] = widget['image']
        if 'data' in widget:
            sim_widget['data'] = widget['data']
        
        return sim_widget

    def convert_from_simulator_format(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simulator scene format back to web designer design format"""
        widgets = scene.get('widgets', [])
        converted = [self.convert_widget_from_sim(w) for w in widgets]
        return {
            'canvas': {
                'width': scene.get('width', 128),
                'height': scene.get('height', 64)
            },
            'widgets': converted
        }

    def convert_widget_from_sim(self, sim_widget: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a simulator widget back to web format"""
        reverse_type_mapping = {
            'LABEL': 'label',
            'BUTTON': 'button',
            'CHECKBOX': 'checkbox',
            'SLIDER': 'slider',
            'PROGRESSBAR': 'progressbar',
            'PANEL': 'panel',
            'LIST': 'list',
            'IMAGE': 'image',
            'ICON': 'icon',
            'GAUGE': 'gauge',
            'CHART': 'chart'
        }
        w = {
            'type': reverse_type_mapping.get(sim_widget.get('type', 'LABEL'), 'label'),
            'x': sim_widget.get('x', 0),
            'y': sim_widget.get('y', 0),
            'width': sim_widget.get('width', 50),
            'height': sim_widget.get('height', 20),
            'text': sim_widget.get('text', ''),
            'id': sim_widget.get('id', '')
        }
        for key in ['bg_color','border','value','checked','min','max','items','icon','image','data']:
            if key in sim_widget:
                # Map bg_color back to color for web
                if key == 'bg_color':
                    w['color'] = sim_widget[key]
                else:
                    w[key] = sim_widget[key]
        return w
    
    async def broadcast_to_designers(self, message: Dict[str, Any], exclude: Optional['WebSocketServerProtocol'] = None) -> None:  # type: ignore[name-defined]
        """Broadcast message to all designer clients, optionally excluding one"""
        if not self.designer_clients:
            return
        
        msg_json = json.dumps(message)
        tasks = [
            client.send(msg_json)
            for client in self.designer_clients
            if exclude is None or client != exclude
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_simulators(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected simulator clients"""
        if not self.simulator_clients:
            return
        
        msg_json = json.dumps(message)
        tasks = [client.send(msg_json) for client in self.simulator_clients]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start(self):
        """Start the bridge server"""
        logger.info(f"Starting WebSocket bridge on ws://{self.host}:{self.port}")
        
        # Retry logic for binding port
        max_retries = 5
        for i in range(max_retries):
            try:
                # Explicitly set reuse_address=True to handle TIME_WAIT
                async with websockets.serve(self.handle_client, self.host, self.port, reuse_address=True):
                    logger.info("Bridge server ready - waiting for connections...")
                    await asyncio.Future()  # Run forever
            except OSError as e:
                if e.errno == 10048:  # Address already in use
                    logger.warning(f"Port {self.port} is busy (attempt {i+1}/{max_retries}). Waiting 1s...")
                    await asyncio.sleep(1)
                else:
                    raise e
        
        logger.error(f"Could not bind to port {self.port} after {max_retries} attempts.")
        sys.exit(1)


async def main():
    """Main entry point"""
    bridge = WebSimBridge(host="localhost", port=8765)
    await bridge.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bridge server stopped by user")
