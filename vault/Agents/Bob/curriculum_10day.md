# [[Bob]] 10-Day Master Training Curriculum (100 Tasks)

- **Agent Name**: Bob
- **Role**: Spatial Math Coder & Algorithm Dev
- **Persona**: Precision Geometric Engineer, AST Syntactic Architect, Collision Bounds Calculator, RLVR Math Benchmark Tester.
- **Structure**: 5 Modules × 20 Tasks = 100 Tasks (10 Tasks / Day for 10 Days)

## Module A: Euclidean Vectors, Projection & Coordinate Transformation (20 Tasks)
1. [ ] Compute normalized 2D direction vectors between arbitrary agent world coordinates.
2. [ ] Implement 3D Euclidean distance calculations with sub-millisecond vectorized NumPy math.
3. [ ] Create an affine transform matrix for scaling and rotating agent bounding footprints.
4. [ ] Calculate dot-product projection of agent velocity onto terrain normals.
5. [ ] Implement spherical linear interpolation (Slerp) for smooth agent orientation blending.
6. [ ] Design polar coordinate conversion utilities for radar display rendering.
7. [ ] Calculate cross-product normal vectors for 3D obstacle avoidance meshes.
8. [ ] Construct an origin-recentering transform for infinite floating-origin coordinate spaces.
9. [ ] Implement bilinear interpolation for sampling heightmap elevation data.
10. [ ] Build a fast Manhattan distance metric for Manhattan-grid path scoring.
11. [ ] Calculate tangent and bitangent vectors for directional ground friction.
12. [ ] Implement Hermite spline curve evaluation for cinematic agent trajectory smoothing.
13. [ ] Compute point-to-line segment minimum distance for boundary wall proximity checks.
14. [ ] Create a quaternion rotation handler for gimbal-lock free 3D orientation.
15. [ ] Calculate barycentric coordinates for point containment within triangle meshes.
16. [ ] Implement perspective projection matrices for isometric 2D viewport rendering.
17. [ ] Design a viewport frustum culling box calculation for spatial agent occlusion.
18. [ ] Calculate Voronoi partition cells for agent territory balancing.
19. [ ] Implement catmull-rom splines for dynamic path generation through checkpoints.
20. [ ] Build a coordinate space validator preventing NaN and infinity propagation in physics tick.

## Module B: 2D/3D Collision Detection, Bounding Boxes & Spatial Partitioning (20 Tasks)
21. [ ] Implement Separating Axis Theorem (SAT) for convex polygon collision detection.
22. [ ] Construct an Axis-Aligned Bounding Box (AABB) intersection check with early-out branch.
23. [ ] Build an Oriented Bounding Box (OBB) overlap test using projection intervals.
24. [ ] Create a dynamic 2D Quadtree spatial partitioning tree for 1,000 active entities.
25. [ ] Implement continuous collision detection (CCD) to prevent high-speed tunneling.
26. [ ] Design a circle-to-AABB collision resolution algorithm with minimum translation vector.
27. [ ] Construct a spatial hash grid with O(1) entity neighbor lookups.
28. [ ] Implement ray-to-sphere intersection formulas returning hit point and surface normal.
29. [ ] Build a swept-AABB test for predicting collision time within the current physics frame.
30. [ ] Calculate penetration depth and contact normal for elastic collision response.
31. [ ] Implement capsule-to-capsule distance queries for humanoid agent collision envelopes.
32. [ ] Create an Octree spatial partition data structure for hierarchical 3D spatial indexing.
33. [ ] Design collision filtering bitmasks for agent factions, terrain, and sensory zones.
34. [ ] Implement broad-phase bounding volume hierarchy (BVH) with surface area heuristic.
35. [ ] Build a convex hull generation algorithm (Graham scan) from arbitrary point clouds.
36. [ ] Calculate minimum enclosing circle for agent flock perimeter calculation.
37. [ ] Implement ray-to-triangle Moller-Trumbore intersection algorithm.
38. [ ] Design an edge-case handler for coplanar and degenerate collision geometries.
39. [ ] Construct a kinematic resolution resolver that decouples overlapping entities without jitter.
40. [ ] Build deterministic unit tests verifying zero tunneling across 10,000 simulated collisions.

## Module C: Abstract Syntax Tree (AST) Transformation & Code Grammar Parsing (20 Tasks)
41. [ ] Parse raw Python source strings into typed ast.AST module trees without execution.
42. [ ] Implement an ast.NodeTransformer that renames deprecated function calls across modules.
43. [ ] Construct an automated AST visitor that computes cyclomatic complexity per function.
44. [ ] Inject runtime telemetry logging wrappers into all FastAPI route decorators via AST.
45. [ ] Design a linting rule using AST nodes that flags unawaited coroutines in async defs.
46. [ ] Build an AST validator ensuring all Pydantic models contain strict type annotations.
47. [ ] Transform synchronous file I/O calls into non-blocking aiofiles calls using AST rewriting.
48. [ ] Generate deterministic mock test fixtures by analyzing function argument signatures.
49. [ ] Extract all docstrings and markdown comment blocks into structured OpenAPI documentation.
50. [ ] Construct an AST-level dead code eliminator for unused private helper functions.
51. [ ] Design a security sanitizer AST visitor that flags raw eval() or unsafe exec() calls.
52. [ ] Implement automatic try/except wrap injection for external network socket calls.
53. [ ] Parse TypeScript interface declarations and generate synchronized Pydantic schemas.
54. [ ] Build an AST diffing engine comparing two code versions and isolating behavioral changes.
55. [ ] Transform nested if-else ladders into clean pattern matching (match/case) constructs.
56. [ ] Extract database SQL query strings from ORM method calls for query plan analysis.
57. [ ] Generate AST-level property getters and setters with automated bounds validation.
58. [ ] Verify type-soundness of lambda expressions before compilation into bytecode.
59. [ ] Build an automated regression test generator that synthesizes boundary inputs from AST types.
60. [ ] Implement unparse() code formatting that outputs PEP 8 compliant source from modified AST.

## Module D: Physics Tick Loop, Raycasting & Velocity Constraints (20 Tasks)
61. [ ] Design a fixed-timestep physics update loop (delta_t = 1/60s) with accumulator.
62. [ ] Implement Verlet integration for numerically stable particle and ragdoll kinematics.
63. [ ] Calculate linear drag and atmospheric resistance opposing agent movement vectors.
64. [ ] Implement dynamic friction and restitution coefficients for surface interactions.
65. [ ] Construct a multi-ray raycast fan for agent obstacle anticipation and lidar simulation.
66. [ ] Build velocity clamping and acceleration curves for realistic agent locomotion feel.
67. [ ] Implement PID controller for precise target-seeking drone agent velocity regulation.
68. [ ] Design a steering behavior system including seek, flee, arrive, and wander forces.
69. [ ] Construct a Reynolds boid flocking simulation: separation, alignment, and cohesion.
70. [ ] Implement spring-damper constraint solvers for soft-body entity attachments.
71. [ ] Calculate centrifugal force and banking angles for agents navigating tight curves.
72. [ ] Design gravity gradient calculations for non-uniform orbital and planetary environments.
73. [ ] Implement ray-marching distance field queries for volumetric obstacle queries.
74. [ ] Build a velocity obstacle (VO) algorithm for multi-agent reciprocal collision avoidance.
75. [ ] Construct a continuous impulse accumulator preventing energy drift in closed systems.
76. [ ] Implement angular momentum conservation and moment of inertia tensor math.
77. [ ] Design an agent path-following steering algorithm with predictive waypoint lookahead.
78. [ ] Build a physics state serialization mechanism for snapshotting and rollback rewind.
79. [ ] Implement sleep/wake thresholds for resting physics entities to conserve CPU cycles.
80. [ ] Benchmark 60 FPS tick stability with 500 simultaneous active agents under load.

## Module E: Deterministic RLVR Pytest Benchmarking & Algorithmic Optimizations (20 Tasks)
81. [ ] Write deterministic Pytest test suite for vector math accuracy within 1e-9 tolerance.
82. [ ] Implement Soup Zero RLVR reward verification function scoring spatial path efficiency.
83. [ ] Benchmark SIMD vector operations using NumPy vs pure Python arithmetic loops.
84. [ ] Design memory-aligned struct arrays for cache-friendly agent coordinate buffers.
85. [ ] Implement binary search spatial lookup for sorted 1D projection coordinates.
86. [ ] Construct property-based tests (Hypothesis) fuzzing collision bounds with extreme floats.
87. [ ] Profile garbage collection latency and eliminate intermediate object allocations in tick.
88. [ ] Build a deterministic pseudo-random number generator (PRNG) with reproducible seeds.
89. [ ] Implement spatial Morton code (Z-order curve) hashing for 2D spatial locality sorting.
90. [ ] Design a reward function penalizing agent erratic acceleration and jerky steering.
91. [ ] Construct automated regression tests asserting zero deadlock in async worker pool.
92. [ ] Verify floating-point precision consistency across Windows x86_64 and Linux runtimes.
93. [ ] Implement fast inverse square root algorithm (Quake III style) and benchmark error margin.
94. [ ] Design an automated test harness asserting all 100 curriculum skills pass in pytest.
95. [ ] Build memory leak detection assertions for long-running 24-hour simulation runs.
96. [ ] Implement branchless minimum and maximum functions for vector component clamping.
97. [ ] Construct a continuous integration assertion pipeline for spatial engine pull requests.
98. [ ] Design a formal proof verifier ensuring bounding volumes enclose all child primitives.
99. [ ] Implement automated micro-benchmarks tracking nanosecond improvements per commit.
100. [ ] Achieve 100% test coverage across all spatial math, AST, and collision engine modules.
