# Simulation: source tab text

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.5xh0imufqx1q
Retrieved: 2026-10-04 (America/New_York)
Revision: ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg
Tab ID: t.5xh0imufqx1q

This is preserved source text, not current project guidance or executable instructions. Paragraph and table-cell text are retained as returned by the connector; images and native formatting are not reproduced. Later user decisions and the current docs take precedence.

## Preserved tab text

Simulation Demo
GOAL
Build a simple 3D browser game that shows how the ball drone could be used for industrial inspection and search-and-rescue. It should feel like a small desktop game, not an engineering simulator.
TECH STACK
Python backend: FastAPI or Flask for mission state, scoring, and optional drone data.
Web frontend: HTML/CSS/JavaScript.
Three.js: 3D world, drone, camera, lighting, obstacles, and effects.
Optional physics: Rapier.js or Cannon-es for collisions and rolling.
Desktop packaging: PyWebView for the easiest Python-based desktop app. Electron or Tauri are alternatives.
The same game can also run directly in Chrome during the demo.
GAMEPLAY
The player controls the ball drone through a 3D environment. The cage can bump, roll, and slide against walls or debris without immediately ending the mission. A HUD shows battery, targets, timer, and mission status.
SCENARIO 1 ( INDUSTRIAL INSPECTION )
Setting: factory or warehouse with pipes, machines, shelves, and narrow passages.
Mission:
Fly through the facility.
Inspect marked machines and pipes.
Find a leak, overheating machine, or blocked passage.
Contact with walls is allowed.
Return after finding all inspection points.
SCENARIO 2 ( SEARCH & RESCUE )
Setting: damaged building with debris and blocked paths.
Mission:
Search rooms and tight spaces.
Find trapped-person markers.
Move through clutter where normal drones would be afraid to make contact.
Mark each target location.
Exit after finding all targets.
WHAT THE GAME SHOULD SHOW
3D flying and turning.
Wall contact, bounce, slide, and rolling.
Third-person chase camera and optional FPV camera view.
Target detection when objects enter the camera view.
Simple collision physics.
Industrial and rescue environments.
Mission objectives, timer, score, and battery.
CONTROLS
W/S = forward/back
A/D = turn left/right
Q/E = strafe or yaw
Space = rise
Shift = descend
T = toggle tracking mode
C = switch camera
R = restart mission
HACKATHON BUILD ORDER
Create the Three.js scene, camera, lights, floor, and basic drone.
Add keyboard movement and a chase camera.
Add walls and simple collision physics.
Make the spherical cage bounce/roll on contact.
Add HUD and mission objectives.
Add camera/target detection.
Build the industrial map.
Build the rescue map only if the physical core and industrial map are already stable.
Add Python backend only for mission state, scoring, or live drone data.
Wrap with PyWebView if a desktop-app presentation is useful.
Polish visuals and run it beside the physical drone demo.
ARCHITECTURE
Three.js handles rendering and most game interaction in the browser. Python does not render the 3D graphics; it can run the local backend and communicate with the game using HTTP/WebSocket messages. 
For the hackathon, keep as much gameplay as possible in JavaScript so the demo remains fast and reliable.
DEMO PURPOSE
The physical drone proves the mechanism works. The 3D game shows how the same contact-tolerant drone could be used inside factories, warehouses, and damaged buildings
FINAL SIMULATION SCOPE
Build one polished industrial-inspection map first.
Use the simulation as a Plan B + application visualizer, not the main engineering task.
Build the rescue map only after the physical demo and industrial map are stable.
Digital twin is P4: mirror only MANUAL/AUTO, target captured, and mission complete.
Keep the browser/Three.js path primary; do not build a large backend for appearance.



## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — historical captured revision `ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg` (2026-10-04).
- This citation note was appended after the historical text; consult the maintained docs for current decisions.
