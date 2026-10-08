#include <cstddef>
#include <Processing.NDI.Lib.h>
#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
#include <cstdlib>
#include <iomanip>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 const std::string wanted=argv[1];
 char* end=nullptr;const long seconds=std::strtol(argv[2],&end,10);
 if(wanted.empty()||!*argv[2]||*end||seconds<1||seconds>3600)return 2;
 if(!NDIlib_initialize())return 1;
 auto finder=NDIlib_find_create_v2(nullptr);if(!finder){NDIlib_destroy();return 1;}NDIlib_recv_instance_t receiver=nullptr;
 for(int retry=0;retry<100&&!receiver;++retry){
  uint32_t count=0;const auto* src=NDIlib_find_get_current_sources(finder,&count);
  for(uint32_t i=0;i<count;++i)if(std::string(src[i].p_ndi_name).find(wanted)!=std::string::npos){
   NDIlib_recv_create_v3_t spec;spec.source_to_connect_to=src[i];spec.color_format=NDIlib_recv_color_format_BGRX_BGRA;
   receiver=NDIlib_recv_create_v3(&spec);break;
  }
  if(!receiver)NDIlib_find_wait_for_sources(finder,200);
 }
 if(!receiver){NDIlib_find_destroy(finder);NDIlib_destroy();return 1;}
 bool videoOn=false,audioOn=false;using Clock=std::chrono::steady_clock;const auto start=Clock::now();
 std::cout<<std::setprecision(6)<<"kind,timecode_s\n";
 while(Clock::now()-start<std::chrono::seconds(seconds)){
  NDIlib_video_frame_v2_t v;NDIlib_audio_frame_v2_t a;NDIlib_metadata_frame_t m;
  const auto type=NDIlib_recv_capture_v2(receiver,&v,&a,&m,100);
  if(type==NDIlib_frame_type_video){
   if(!v.p_data||v.xres<=0||v.yres<=0||v.line_stride_in_bytes<v.xres*4){NDIlib_recv_free_video_v2(receiver,&v);continue;}
   const auto* px=v.p_data+(v.yres/2)*v.line_stride_in_bytes+(v.xres/2)*4;
   const bool on=(int(px[0])+px[1]+px[2])>360;
   if(on&&!videoOn)std::cout<<"video,"<<std::fixed<<double(v.timecode)/1e7<<'\n';
   videoOn=on;NDIlib_recv_free_video_v2(receiver,&v);
  }else if(type==NDIlib_frame_type_audio){
   if(!a.p_data||a.sample_rate<=0||a.no_channels<=0){NDIlib_recv_free_audio_v2(receiver,&a);continue;}
   for(int n=0;n<a.no_samples;n+=48){
    bool on=false;for(int k=n;k<a.no_samples&&k<n+48;++k)on=on||std::abs(a.p_data[k])>.1f;
    if(on&&!audioOn)std::cout<<"audio,"<<std::fixed<<(double(a.timecode)/1e7+double(n)/a.sample_rate)<<'\n';
    audioOn=on;
   }
   NDIlib_recv_free_audio_v2(receiver,&a);
  }else if(type==NDIlib_frame_type_metadata)NDIlib_recv_free_metadata(receiver,&m);
 }
 NDIlib_recv_destroy(receiver);NDIlib_find_destroy(finder);NDIlib_destroy();
}
