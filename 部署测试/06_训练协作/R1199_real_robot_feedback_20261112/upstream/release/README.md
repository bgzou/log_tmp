# AS2-W rolling 1199 simulation preview

1200 training iterations. ONNX opset 17, input 1 x 65, output 1 x 16. Parity covers 7,560 recorded frames with maximum action error 8.59e-6. Verify the checkpoint and ONNX hashes against onnx-parity.json.

Use the official reference and shadow contract for SDK motor slots, joint names and sign conventions. Verify the mapping on the target calibration and match evaluation preprocessing and action scaling. The included preflight and deployment archive are for offline integration. The older R284 runtime is not compatible based on tensor dimensions alone.

Map joystick input to longitudinal speed and yaw with lateral command zero. Integrate the braking and fixed-exit helpers with fixed stand at entry and after neutral braking and settling. Keep the 90% joint angle and total torque guards, contact checks, and watchdog active. Keep motor output disabled in shadow mode.

Behavior acceptance remains open. At 0.30 m/s there is parking drift and incomplete fixed-stand holding. Left and right turns did not pass the complete sequence. None of the 1, 2, or 3 m/s stages cleared dual simulator acceptance. Use this candidate for simulation or offline shadow work.
