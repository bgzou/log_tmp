#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace as2w_mlp57 {
using Vec3=std::array<float,3>;
using Vec16=std::array<float,16>;
using Obs=std::array<float,57>;
inline constexpr Vec16 q0={0,.65f,-1.3f,0,.65f,-1.3f,0,.65f,-1.3f,0,.65f,-1.3f,0,0,0,0};
inline float clip(float x) { return std::max(-100.f,std::min(100.f,x)); }
inline Obs observation(const Vec3& gyro,const Vec3& gravity,const Vec3& command,
                       const Vec16& q,const Vec16& dq,const Vec16& previous) {
    Obs out{};
    for(int i=0;i<3;++i) {
        out[i]=clip(gyro[i])*.25f;
        out[3+i]=clip(gravity[i]);
        out[6+i]=clip(command[i]);
    }
    for(int i=0;i<16;++i) {
        out[9+i]=clip(i<12 ? q[i]-q0[i] : 0.f);
        out[25+i]=clip(dq[i])*.05f;
        out[41+i]=clip(previous[i]);
    }
    return out;
}
struct Targets { Vec16 q_des{},dq_des{},kp{},kd{},tau_ff{},next_previous_raw_action{}; };
inline Targets targets(const Vec16& raw) {
    Targets out;
    out.q_des=q0;
    for(int i=0;i<16;++i) {
        if(!std::isfinite(raw[i])) throw std::invalid_argument("nonfinite raw action");
        if(i<12) {
            out.q_des[i]=clip(raw[i]*(i%3==0 ? .125f : .25f)+q0[i]);
            out.kp[i]=40.f;
        } else out.dq_des[i]=clip(raw[i]*5.f);
        out.kd[i]=1.f;
        out.next_previous_raw_action[i]=raw[i];
    }
    return out;
}
} // policy-order targets only; no DDS slot map, control publisher or robot FSM
