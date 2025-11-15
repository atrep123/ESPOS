Import("env")
import os
import subprocess

def run_simulator(*args, **kwargs):
    """Run the compiled simulator executable"""
    # Get the program path from the environment
    program_path = env.get("PROGPATH")
    
    if program_path and os.path.exists(program_path):
        print("\n" + "="*70)
        print("Running UI Simulator...")
        print("="*70 + "\n")
        
        # Run the executable
        try:
            result = subprocess.run([program_path], check=False)
            print("\n" + "="*70)
            print(f"Simulator exited with code: {result.returncode}")
            print("="*70)
        except Exception as e:
            print(f"Error running simulator: {e}")
    else:
        print(f"Simulator executable not found at: {program_path}")

# Add custom target for running
env.AlwaysBuild(env.Alias("run", env.get("PROGPATH"), run_simulator))
