"""Small, deterministic longitudinal motion helpers."""
def integrate_speed(speed, throttle, brake, acceleration, braking, dt, max_speed):
    if brake > 0:
        speed = max(0.0, speed - braking * brake * dt)
    else:
        speed = min(max_speed, speed + acceleration * throttle * dt)
    return speed
