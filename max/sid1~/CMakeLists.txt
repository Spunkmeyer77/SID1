set_property(DIRECTORY PROPERTY max::external YES)
project(sid1_tilde C)
target_sources(sid1_tilde PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/sid1~.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/../../engine/sid1_engine.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/../../core/sid.c")
if(MSVC)
  target_compile_options(sid1_tilde PRIVATE /O2)
else()
  target_compile_options(sid1_tilde PRIVATE -O2)
endif()
