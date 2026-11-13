"""Rolling residual action mapping with command-gated fixed stand."""
def rolling_fixed_exit(raw, command):
    vx, yaw = command[:, :1], command[:, 2:3]
    turning = (yaw.abs() / .20).clamp(max=1.)
    motion = ((vx.abs() / .10).maximum(turning)).clamp(max=1.)
    side = raw.new_tensor((1., -1., 1., -1.))
    wheel = raw[:, 12:].clamp(-1., 1.)
    common = wheel.mean(dim=1, keepdim=True)
    steering = (wheel * side).mean(dim=1, keepdim=True)
    legs = .18 * motion * raw[:, :12].clamp(-1., 1.)
    linear = vx + .10 * turning * common - .66 * (1. + .25 * steering) * yaw * side
    wheels = linear / (.086 * 16.) + .035 * motion * (1. - turning) * (wheel - common)
    return legs, wheels.clamp(-6., 6.)


def mirror_rolling_joints(frame):
    pairs = (1,0,3,2,5,4,7,6,9,8,11,10,13,12,15,14)
    reflected = frame[:,pairs].clone()
    reflected[:,:4] *= -1.
    return reflected


def mirror_rolling_observation(frame):
    reflected = frame.clone()
    reflected[:,[1,2,3,5,7]] *= -1.
    for start in (10,26,42):
        reflected[:,start:start+16] = mirror_rolling_joints(frame[:,start:start+16])
    if frame.shape[-1] == 65:
        reflected[:,60:64] = frame[:,[61,60,63,62]]
    return reflected


def rolling_stand_bias(bias, command, q_error, gyro, up, wheel_speed, dt, *, enabled=None):
    """Compensate static joint deflection only around centered-stick standing."""
    import torch

    activity = (command[:,:1].abs()/.08).maximum(command[:,2:3].abs()/.15)
    quiet = ((gyro.norm(dim=1)<.30) & (up>.90)
             & (wheel_speed.abs().amax(dim=1)<1.2))
    integrate = (activity[:,0]<.05) & quiet
    if enabled is not None:
        integrate &= enabled
    candidate = ((1.-.04*dt)*bias - 2.*dt*q_error).clamp(-.44,.44)
    bias = torch.where(integrate[:,None],candidate,bias)
    bias = torch.where((activity<1.) & (up[:,None]>.85),bias,0.)
    return bias, (1.-activity).clamp(0.,1.)*bias/.35


def rolling_wheel_hold(reference, frames, command, wheel_angle, wheel_speed, gyro, dt):
    """Latch wheel position after braking, with wrapped angle feedback."""
    import torch

    centered = command.abs().amax(dim=1) < .005
    quiet = (wheel_speed.abs().amax(dim=1)<.50) & (gyro.norm(dim=1)<.15)
    latched = frames*dt >= .12
    frames = torch.where(centered & (latched | quiet),frames+1,0)
    capture = (frames*dt>=.12) & ~latched
    reference = torch.where(capture[:,None],wheel_angle,reference)
    error = (wheel_angle-reference+2.*torch.pi).remainder(4.*torch.pi)-2.*torch.pi
    target = (-6.*error).clamp(-1.5,1.5)/16.
    return reference,frames,target*(frames*dt>=.12)[:,None]


def rolling_precalibrated_stand(bias, command, q_error, gyro, up, wheel_speed, frames, age, dt):
    """Calibrate under initial support, then reuse the frozen standing offset."""
    import torch

    activity = (command[:,:1].abs()/.08).maximum(command[:,2:3].abs()/.15)
    quiet = ((gyro.norm(dim=1)<.20) & (up>.92) & (wheel_speed.abs().amax(dim=1)<.55))
    calibrate = (age < 4.) & quiet & (frames*dt>=.30) & (activity[:,0]<.05)
    correction = (-1.40*dt*q_error).clamp(-.004,.004)
    candidate = ((1.-.03*dt)*bias + correction).clamp(-.38,.38)
    bias = torch.where(calibrate[:,None],candidate,bias)
    release_blend = ((frames*dt-.45)/1.05).clamp(0.,1.)
    blend = torch.where(age<4.,torch.ones_like(release_blend),release_blend)
    output = blend[:,None]*(1.-activity).clamp(0.,1.)*bias/.35
    return bias,output
