AS2-W offline deployment preview
=================================

This bundle validates normalized observations and policy transitions offline.
It has no DDS client and does not emit motor targets or torque. The official
reference uses URDF simulation geometry and limits. Hardware DDS slots,
directions, offsets, and hardware derating are deliberately unset.

Run with the Python environment used for ONNX export. The replay dependencies
are numpy and onnxruntime. The diagnostic controller source files also use torch.

1. Run python as2w_deploy_preflight.py as2w-official-reference.json MODEL_DIR
   on each candidate directory containing policy.onnx and onnx-parity.json.
   Adding --require-hardware-map verifies the binding requirement and rejects
   the provided reference for real actuation.

2. Prepare JSONL with one row per 20 ms policy frame. Each row contains
   feedback, request, and observations. The Feedback data fields are defined
   in as2w_mode_switch.py. Request is rolling, stepping, getup, or null.
   Observations is a dictionary keyed by policy with the normalized frame
   defined in as2w-shadow-contract.json. Range endings are exclusive.

3. Run python as2w_shadow_replay.py as2w-official-reference.json input.jsonl
   result.jsonl --rolling ROLL_DIR --stepping STEP_DIR --getup GETUP_DIR
   on one command line. Review phase, policy, blend weight, centered-command
   and observation-reset flags, and latched fault. Raw actor output is logged
   for comparison and is not interpreted as a hardware actuator command.

Acceptance evidence for this preview used 550 frames with recorded simulation
observations and a scripted feedback timeline. Full closed-loop transitions
in both physics engines, robot-specific LowState mapping, and deployment
qualification remain separate gates.
