#include "../runtime/reference.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
int main() {
    std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
    std::array<float,73> x{};
    while(std::cin>>x[0]) {
        for(int i=1;i<73;++i) if(!(std::cin>>x[i])) return 2;
        for(float value:x) if(!std::isfinite(value)) return 3;
        as2w_mlp57::Vec3 gyro{},gravity{},command{};
        as2w_mlp57::Vec16 q{},dq{},previous{},raw{};
        for(int i=0;i<3;++i) {gyro[i]=x[i];gravity[i]=x[3+i];command[i]=x[6+i];}
        for(int i=0;i<16;++i) {q[i]=x[9+i];dq[i]=x[25+i];previous[i]=x[41+i];raw[i]=x[57+i];}
        auto obs=as2w_mlp57::observation(gyro,gravity,command,q,dq,previous);
        auto target=as2w_mlp57::targets(raw);
        bool first=true;
        auto emit=[&](const auto& values){for(auto value:values){if(!first)std::cout<<' ';first=false;std::cout<<value;}};
        emit(obs);emit(target.q_des);emit(target.dq_des);emit(target.kp);emit(target.kd);emit(target.tau_ff);emit(target.next_previous_raw_action);
        std::cout<<'\n';
    }
}
