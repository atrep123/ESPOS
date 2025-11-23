#!/usr/bin/env python3
"""
Animation Timeline Editor Demo
Demonstrates keyframe-based animation creation
"""

from ui_animations import AnimationDesigner, Animation, AnimationType, EasingFunction, Keyframe
import json


def create_demo_animations():
    """Create example animations with keyframes"""
    designer = AnimationDesigner()
    
    # 1. Simple fade in
    fade_in = Animation(
        name="fade_in",
        type=AnimationType.FADE.value,
        duration=500,
        easing=EasingFunction.EASE_IN_OUT.value,
        iterations=1,
        keyframes=[
            Keyframe(time=0.0, properties={"opacity": 0.0}, easing="linear"),
            Keyframe(time=1.0, properties={"opacity": 1.0}, easing="linear")
        ]
    )
    designer.register_animation(fade_in)
    
    # 2. Slide from left with fade
    slide_fade = Animation(
        name="slide_fade",
        type=AnimationType.SLIDE_LEFT.value,
        duration=800,
        easing=EasingFunction.EASE_OUT.value,
        iterations=1,
        keyframes=[
            Keyframe(time=0.0, properties={"x": -100, "opacity": 0.0}, easing="ease_out"),
            Keyframe(time=0.5, properties={"x": -20, "opacity": 0.5}, easing="ease_out"),
            Keyframe(time=1.0, properties={"x": 0, "opacity": 1.0}, easing="linear")
        ]
    )
    designer.register_animation(slide_fade)
    
    # 3. Bounce effect
    bounce = Animation(
        name="bounce",
        type=AnimationType.BOUNCE.value,
        duration=1200,
        easing=EasingFunction.EASE_OUT_BOUNCE.value,
        iterations=-1,  # Infinite loop
        keyframes=[
            Keyframe(time=0.0, properties={"y": 0, "scale": 1.0}, easing="ease_out_bounce"),
            Keyframe(time=0.5, properties={"y": 50, "scale": 0.8}, easing="ease_in"),
            Keyframe(time=1.0, properties={"y": 0, "scale": 1.0}, easing="ease_out_bounce")
        ]
    )
    designer.register_animation(bounce)
    
    # 4. Pulse effect
    pulse = Animation(
        name="pulse",
        type=AnimationType.PULSE.value,
        duration=1000,
        easing=EasingFunction.EASE_IN_OUT.value,
        iterations=-1,
        keyframes=[
            Keyframe(time=0.0, properties={"scale": 1.0, "opacity": 1.0}, easing="ease_in_out"),
            Keyframe(time=0.5, properties={"scale": 1.15, "opacity": 0.8}, easing="ease_in_out"),
            Keyframe(time=1.0, properties={"scale": 1.0, "opacity": 1.0}, easing="ease_in_out")
        ]
    )
    designer.register_animation(pulse)
    
    # 5. Complex path animation
    complex_path = Animation(
        name="complex_path",
        type=AnimationType.MOVE.value,
        duration=2000,
        easing=EasingFunction.LINEAR.value,
        iterations=1,
        keyframes=[
            Keyframe(time=0.0, properties={"x": 0, "y": 0, "rotation": 0}, easing="linear"),
            Keyframe(time=0.25, properties={"x": 100, "y": 0, "rotation": 90}, easing="ease_in"),
            Keyframe(time=0.5, properties={"x": 100, "y": 100, "rotation": 180}, easing="ease_out"),
            Keyframe(time=0.75, properties={"x": 0, "y": 100, "rotation": 270}, easing="ease_in"),
            Keyframe(time=1.0, properties={"x": 0, "y": 0, "rotation": 360}, easing="ease_out")
        ]
    )
    designer.register_animation(complex_path)
    
    return designer


def export_animations(designer: AnimationDesigner, filename: str = "demo_animations.json"):
    """Export animations to JSON file"""
    data = {
        "animations": []
    }
    
    for name, anim in designer.animations.items():
        anim_data = {
            "name": anim.name,
            "type": anim.type,
            "duration": anim.duration,
            "easing": anim.easing,
            "iterations": anim.iterations,
            "keyframes": [
                {
                    "time": kf.time,
                    "properties": kf.properties,
                    "easing": kf.easing
                }
                for kf in anim.keyframes
            ]
        }
        data["animations"].append(anim_data)
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Exported {len(designer.animations)} animations to {filename}")


def print_animation_summary(designer: AnimationDesigner):
    """Print summary of all animations"""
    print("\n" + "="*60)
    print("ANIMATION TIMELINE DEMO - Summary")
    print("="*60 + "\n")
    
    for name in designer.list_animations():
        anim = designer.animations[name]
        print(f"📽️  {anim.name}")
        print(f"   Type: {anim.type}")
        print(f"   Duration: {anim.duration}ms")
        print(f"   Easing: {anim.easing}")
        print(f"   Loop: {'Yes' if anim.iterations == -1 else 'No'}")
        print(f"   Keyframes: {len(anim.keyframes)}")
        
        if anim.keyframes:
            print("   Timeline:")
            for i, kf in enumerate(anim.keyframes):
                props_str = ", ".join([f"{k}={v}" for k, v in kf.properties.items()])
                print(f"      [{i}] t={kf.time:.2f} → {props_str} ({kf.easing})")
        
        print()


def main():
    """Run animation timeline demo"""
    print("Creating demo animations...")
    designer = create_demo_animations()
    
    print_animation_summary(designer)
    
    export_animations(designer, "demo_animations.json")
    
    print("\n✅ Demo complete!")
    print("\nTo view these animations:")
    print("  1. Run: python ui_designer_preview.py")
    print("  2. Add a widget to the canvas")
    print("  3. Click the ✏ Edit button")
    print("  4. Select an animation from the dropdown")
    print("  5. Click ▶ to preview")
    print("\nOr load demo_animations.json into the UI Designer.")


if __name__ == "__main__":
    main()
