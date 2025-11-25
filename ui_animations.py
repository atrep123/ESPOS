#!/usr/bin/env python3
"""
Animation Designer for UI Designer
Screen transitions, widget animations, and keyframe editor
"""

import json
import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AnimationType(Enum):
    """Available animation types"""

    # Screen transitions
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DISSOLVE = "dissolve"

    # Widget animations
    MOVE = "move"
    RESIZE = "resize"
    ROTATE = "rotate"
    OPACITY = "opacity"
    SCALE = "scale"
    COLOR = "color"

    # Combined animations
    BOUNCE = "bounce"
    SHAKE = "shake"
    PULSE = "pulse"
    FLIP = "flip"


class EasingFunction(Enum):
    """Easing functions for smooth animations"""

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    EASE_IN_QUAD = "ease_in_quad"
    EASE_OUT_QUAD = "ease_out_quad"
    EASE_IN_OUT_QUAD = "ease_in_out_quad"
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"
    EASE_IN_ELASTIC = "ease_in_elastic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_OUT_BOUNCE = "ease_out_bounce"


@dataclass
class Keyframe:
    """Single keyframe in animation"""

    time: float  # 0.0 to 1.0
    properties: Dict[str, Any]  # Property name -> value
    easing: str = "linear"


@dataclass
class Animation:
    """Animation definition"""

    name: str
    type: str
    duration: int  # milliseconds
    delay: int = 0
    iterations: int = 1  # -1 for infinite
    direction: str = "normal"  # normal, reverse, alternate
    easing: str = "ease_in_out"
    keyframes: List[Keyframe] = field(default_factory=list)

    # Target
    widget_id: Optional[int] = None
    scene_name: Optional[str] = None

    # Animation-specific parameters
    start_value: Any = None
    end_value: Any = None

    # State
    current_iteration: int = 0
    start_time: Optional[float] = None
    is_playing: bool = False


@dataclass
class Transition:
    """Scene transition definition"""

    name: str
    type: str
    duration: int
    easing: str = "ease_in_out"
    from_scene: str = ""
    to_scene: str = ""


class AnimationEasing:
    """Easing function implementations"""

    @staticmethod
    def linear(t: float) -> float:
        """Linear easing"""
        return t

    @staticmethod
    def ease_in(t: float) -> float:
        """Ease in (slow start)"""
        return t * t

    @staticmethod
    def ease_out(t: float) -> float:
        """Ease out (slow end)"""
        return t * (2 - t)

    @staticmethod
    def ease_in_out(t: float) -> float:
        """Ease in-out (slow start and end)"""
        return t * t * (3 - 2 * t)

    @staticmethod
    def ease_in_quad(t: float) -> float:
        """Quadratic ease in"""
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        """Quadratic ease out"""
        return t * (2 - t)

    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        """Quadratic ease in-out"""
        if t < 0.5:
            return 2 * t * t
        return -1 + (4 - 2 * t) * t

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        """Cubic ease in"""
        return t * t * t

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        """Cubic ease out"""
        return (t - 1) * (t - 1) * (t - 1) + 1

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Cubic ease in-out"""
        if t < 0.5:
            return 4 * t * t * t
        return (t - 1) * (2 * t - 2) * (2 * t - 2) + 1

    @staticmethod
    def ease_in_elastic(t: float) -> float:
        """Elastic ease in"""
        if t == 0 or t == 1:
            return t
        return -(2 ** (10 * (t - 1))) * math.sin((t - 1.1) * 5 * math.pi)

    @staticmethod
    def ease_out_elastic(t: float) -> float:
        """Elastic ease out"""
        if t == 0 or t == 1:
            return t
        return (2 ** (-10 * t)) * math.sin((t - 0.1) * 5 * math.pi) + 1

    @staticmethod
    def ease_out_bounce(t: float) -> float:
        """Bounce ease out"""
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375

    @staticmethod
    def get_easing(name: str) -> Callable[[float], float]:
        """Get easing function by name"""
        easing_map = {
            "linear": AnimationEasing.linear,
            "ease_in": AnimationEasing.ease_in,
            "ease_out": AnimationEasing.ease_out,
            "ease_in_out": AnimationEasing.ease_in_out,
            "ease_in_quad": AnimationEasing.ease_in_quad,
            "ease_out_quad": AnimationEasing.ease_out_quad,
            "ease_in_out_quad": AnimationEasing.ease_in_out_quad,
            "ease_in_cubic": AnimationEasing.ease_in_cubic,
            "ease_out_cubic": AnimationEasing.ease_out_cubic,
            "ease_in_out_cubic": AnimationEasing.ease_in_out_cubic,
            "ease_in_elastic": AnimationEasing.ease_in_elastic,
            "ease_out_elastic": AnimationEasing.ease_out_elastic,
            "ease_out_bounce": AnimationEasing.ease_out_bounce,
        }
        return easing_map.get(name, AnimationEasing.linear)


class AnimationDesigner:
    """Animation designer and player"""

    def __init__(self):
        self.animations: Dict[str, Animation] = {}
        self.transitions: Dict[str, Transition] = {}
        self.active_animations: List[str] = []

        # Register built-in animations
        self._register_builtin_animations()
        self._register_builtin_transitions()

    def _register_builtin_animations(self):
        """Register built-in animation templates (simplified for embedded use)"""

        # Fade in - simple opacity change, low memory
        fade_in = Animation(
            name="FadeIn",
            type=AnimationType.OPACITY.value,
            duration=300,
            easing="ease_in",
            start_value=0,
            end_value=100,
        )

        # Slide in from left - simple position offset
        slide_in = Animation(
            name="SlideIn",
            type=AnimationType.SLIDE_LEFT.value,
            duration=250,
            easing="ease_out",
            keyframes=[
                Keyframe(time=0.0, properties={"x_offset": -30}),
                Keyframe(time=1.0, properties={"x_offset": 0}),
            ],
        )

        # Pulse - for notifications/alerts (infinite loop)
        pulse = Animation(
            name="Pulse",
            type=AnimationType.PULSE.value,
            duration=600,
            iterations=-1,  # Infinite
            easing="ease_in_out",
            keyframes=[
                Keyframe(time=0.0, properties={"opacity": 100}),
                Keyframe(time=0.5, properties={"opacity": 60}),
                Keyframe(time=1.0, properties={"opacity": 100}),
            ],
        )

        for anim in [fade_in, slide_in, pulse]:
            self.register_animation(anim)

    def _register_builtin_transitions(self):
        """Register built-in scene transitions (simplified for embedded use)"""

        transitions = [
            Transition("Fade", AnimationType.FADE.value, 250, "ease_in_out"),
            Transition("SlideLeft", AnimationType.SLIDE_LEFT.value, 300, "ease_out"),
            Transition("SlideRight", AnimationType.SLIDE_RIGHT.value, 300, "ease_out"),
        ]

        for trans in transitions:
            self.register_transition(trans)

    def register_animation(self, animation: Animation):
        """Register an animation"""
        self.animations[animation.name] = animation

    def register_transition(self, transition: Transition):
        """Register a transition"""
        self.transitions[transition.name] = transition

    def create_animation(
        self, name: str, animation_type: str, duration: int, **kwargs
    ) -> Animation:
        """Create custom animation"""
        anim = Animation(name=name, type=animation_type, duration=duration, **kwargs)
        self.register_animation(anim)
        return anim

    def add_keyframe(
        self, animation_name: str, time: float, properties: Dict[str, Any], easing: str = "linear"
    ):
        """Add keyframe to animation"""
        anim = self.animations.get(animation_name)
        if not anim:
            raise ValueError(f"Animation '{animation_name}' not found")

        keyframe = Keyframe(time=time, properties=properties, easing=easing)
        anim.keyframes.append(keyframe)

        # Sort keyframes by time
        anim.keyframes.sort(key=lambda k: k.time)

    def play_animation(self, animation_name: str, widget_id: Optional[int] = None):
        """Start playing an animation"""
        anim = self.animations.get(animation_name)
        if not anim:
            raise ValueError(f"Animation '{animation_name}' not found")

        anim.widget_id = widget_id
        anim.start_time = time.time()
        anim.is_playing = True
        anim.current_iteration = 0

        if animation_name not in self.active_animations:
            self.active_animations.append(animation_name)

    def stop_animation(self, animation_name: str):
        """Stop playing an animation"""
        anim = self.animations.get(animation_name)
        if anim:
            anim.is_playing = False
            if animation_name in self.active_animations:
                self.active_animations.remove(animation_name)

    def update_animations(self) -> Dict[str, Dict[str, Any]]:
        """Update all active animations and return current values"""
        results = {}

        for anim_name in self.active_animations:
            anim = self.animations[anim_name]

            if not anim.is_playing or anim.start_time is None:
                continue

            # Calculate elapsed time
            elapsed = (time.time() - anim.start_time) * 1000  # ms
            elapsed -= anim.delay

            if elapsed < 0:
                continue

            # Calculate progress (0.0 to 1.0)
            progress = min(elapsed / anim.duration, 1.0)

            # Apply easing
            easing_func = AnimationEasing.get_easing(anim.easing)
            eased_progress = easing_func(progress)

            # Calculate current values
            values = self._calculate_animation_values(anim, eased_progress)
            results[anim_name] = values

            # Check if animation is complete
            if progress >= 1.0:
                anim.current_iteration += 1

                if anim.iterations == -1:  # Infinite
                    anim.start_time = time.time()
                elif anim.current_iteration >= anim.iterations:
                    self.stop_animation(anim_name)
                else:
                    anim.start_time = time.time()

        return results

    def _interpolate_simple_animation(self, anim: Animation, progress: float) -> Dict[str, Any]:
        """Interpolate simple start/end animation."""
        if anim.start_value is None or anim.end_value is None:
            return {}
        if isinstance(anim.start_value, (int, float)):
            value = anim.start_value + (anim.end_value - anim.start_value) * progress
            return {anim.type: value}
        return {}

    def _find_surrounding_keyframes(self, keyframes: list, progress: float) -> tuple:
        """Find keyframes surrounding the given progress point."""
        prev_kf = keyframes[0]
        next_kf = keyframes[-1]

        for kf in keyframes:
            if kf.time <= progress:
                prev_kf = kf
            elif kf.time > progress and next_kf == keyframes[-1]:
                next_kf = kf
                break

        return prev_kf, next_kf

    def _interpolate_keyframe_properties(
        self, prev_kf, next_kf, eased_progress: float
    ) -> Dict[str, Any]:
        """Interpolate properties between two keyframes."""
        result = {}
        for key in prev_kf.properties:
            if key in next_kf.properties:
                start = prev_kf.properties[key]
                end = next_kf.properties[key]

                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    result[key] = start + (end - start) * eased_progress
                else:
                    result[key] = end if eased_progress > 0.5 else start

        return result

    def _calculate_animation_values(self, anim: Animation, progress: float) -> Dict[str, Any]:
        """Calculate current animation values based on progress"""
        if not anim.keyframes:
            return self._interpolate_simple_animation(anim, progress)

        # Keyframe-based animation
        prev_kf, next_kf = self._find_surrounding_keyframes(anim.keyframes, progress)

        # If same keyframe, return its properties
        if prev_kf == next_kf:
            return prev_kf.properties.copy()

        # Calculate local progress between keyframes
        kf_duration = next_kf.time - prev_kf.time
        local_progress = 1.0 if kf_duration == 0 else (progress - prev_kf.time) / kf_duration

        # Apply keyframe easing
        easing_func = AnimationEasing.get_easing(next_kf.easing)
        eased_local = easing_func(local_progress)

        # Interpolate properties
        return self._interpolate_keyframe_properties(prev_kf, next_kf, eased_local)

    def apply_transition(self, from_scene: str, to_scene: str, transition_name: str = "Fade"):
        """Apply transition between scenes"""
        trans = self.transitions.get(transition_name)
        if not trans:
            raise ValueError(f"Transition '{transition_name}' not found")

        trans.from_scene = from_scene
        trans.to_scene = to_scene

        return trans

    def export_animation(self, animation_name: str, filename: str):
        """Export animation to JSON"""
        anim = self.animations.get(animation_name)
        if not anim:
            raise ValueError(f"Animation '{animation_name}' not found")

        anim_dict = asdict(anim)
        with open(filename, "w") as f:
            json.dump(anim_dict, f, indent=2)

    def import_animation(self, filename: str) -> Animation:
        """Import animation from JSON"""
        with open(filename, "r") as f:
            data = json.load(f)

        # Convert keyframes
        keyframes = [Keyframe(**kf) for kf in data.get("keyframes", [])]
        data["keyframes"] = keyframes

        anim = Animation(**data)
        self.register_animation(anim)
        return anim

    def preview_animation(self, animation_name: str) -> str:
        """Generate ASCII preview of animation timeline"""
        anim = self.animations.get(animation_name)
        if not anim:
            return f"Animation '{animation_name}' not found"

        preview = f"""
╔══════════════════════════════════════════════════════════╗
║ {anim.name:<54} ║
╠══════════════════════════════════════════════════════════╣
║ Type: {anim.type:<50} ║
║ Duration: {anim.duration}ms{' '*(46-len(str(anim.duration)))}║
║ Easing: {anim.easing:<48} ║
║ Iterations: {anim.iterations if anim.iterations != -1 else 'infinite':<45} ║
╠══════════════════════════════════════════════════════════╣
║ TIMELINE                                                 ║
╠══════════════════════════════════════════════════════════╣
"""

        # Draw timeline
        timeline = "║ 0%  "
        for i in range(50):
            progress = i / 50
            has_keyframe = any(abs(kf.time - progress) < 0.02 for kf in anim.keyframes)
            timeline += "●" if has_keyframe else "─"
        timeline += " 100% ║\n"
        preview += timeline

        # Keyframes
        if anim.keyframes:
            preview += "╠══════════════════════════════════════════════════════════╣\n"
            preview += "║ KEYFRAMES                                                ║\n"
            preview += "╠══════════════════════════════════════════════════════════╣\n"
            for kf in anim.keyframes:
                time_pct = int(kf.time * 100)
                props_str = ", ".join(f"{k}={v}" for k, v in kf.properties.items())
                if len(props_str) > 40:
                    props_str = props_str[:37] + "..."
                preview += f"║ {time_pct:3d}% - {props_str:<46} ║\n"

        preview += "╚══════════════════════════════════════════════════════════╝\n"

        return preview

    def list_animations(self) -> List[str]:
        """List all registered animations"""
        return list(self.animations.keys())

    def list_transitions(self) -> List[str]:
        """List all registered transitions"""
        return list(self.transitions.keys())


def main():
    """Demo animation designer"""
    print("⚡ UI DESIGNER ANIMATION SYSTEM\n")

    designer = AnimationDesigner()

    print("Built-in Animations:")
    for anim_name in designer.list_animations():
        anim = designer.animations[anim_name]
        print(f"  • {anim_name} ({anim.duration}ms) - {anim.type}")

    print("\nBuilt-in Transitions:")
    for trans_name in designer.list_transitions():
        trans = designer.transitions[trans_name]
        print(f"  • {trans_name} ({trans.duration}ms) - {trans.type}")

    print("\n" + "=" * 60)

    # Preview animations
    for anim_name in ["FadeIn", "Pulse", "Shake"]:
        print(designer.preview_animation(anim_name))

    # Create custom animation
    print("\n🎨 Creating custom animation...")
    custom = designer.create_animation(
        name="CustomMove", animation_type="move", duration=1000, easing="ease_in_out_cubic"
    )
    designer.add_keyframe("CustomMove", 0.0, {"x": 0, "y": 0})
    designer.add_keyframe("CustomMove", 0.5, {"x": 50, "y": 25})
    designer.add_keyframe("CustomMove", 1.0, {"x": 100, "y": 0})
    print(f"✓ Created '{custom.name}'")
    print(designer.preview_animation("CustomMove"))

    # Export example
    print("\n📦 Exporting 'Pulse' animation...")
    designer.export_animation("Pulse", "animation_pulse.json")
    print("✓ Saved to animation_pulse.json")

    # Simulate animation playback
    print("\n▶️  Simulating 'Bounce' animation playback...")
    designer.play_animation("Bounce")

    for i in range(10):
        values = designer.update_animations()  # Update all animations
        if "Bounce" in values:
            print(f"  Frame {i}: {values['Bounce']}")
        time.sleep(0.05)

    print("\n✅ Animation system ready!")
    print(f"   Total animations: {len(designer.animations)}")
    print(f"   Total transitions: {len(designer.transitions)}")


if __name__ == "__main__":
    main()
